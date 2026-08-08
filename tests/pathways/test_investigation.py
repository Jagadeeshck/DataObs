from datetime import datetime, timezone

import pytest

from packages.pathways.investigation import (
    HistoricalEdge,
    HistoricalNode,
    InvestigationAnchor,
    TraversalRequest,
    WindowMetric,
    canonical_graph_hash,
    compare_metric,
)
from packages.pathways.traversal import traverse


def node(name: str, **values: object) -> HistoricalNode:
    return HistoricalNode(name, str(values.pop("node_type", "topic")), name, **values)


def edge(name: str, source: str, destination: str, **values: object) -> HistoricalEdge:
    return HistoricalEdge(name, source, destination, str(values.pop("relationship", "flows_to")), **values)


def request(direction: str = "downstream", **limits: int) -> TraversalRequest:
    return TraversalRequest(InvestigationAnchor("topic", "A"), direction, **limits)


@pytest.mark.parametrize(
    "direction,expected", [("downstream", ["A", "B", "C"]), ("upstream", ["A"]), ("both", ["A", "B", "C"])]
)
def test_linear_direction(direction: str, expected: list[str]) -> None:
    result = traverse([node(x) for x in "ABC"], [edge("ab", "A", "B"), edge("bc", "B", "C")], request(direction))
    assert [path.entity_id for path in result.paths] == expected


def test_upstream_fan_in_and_cycle_are_deterministic() -> None:
    nodes = [node(x) for x in "ABCD"]
    edges = [edge("ca", "C", "A"), edge("ba", "B", "A"), edge("ad", "A", "D"), edge("da", "D", "A")]
    first = traverse(nodes, edges, request("both"))
    second = traverse(list(reversed(nodes)), list(reversed(edges)), request("both"))
    assert first == second
    assert [p.entity_id for p in first.paths] == ["A", "B", "C", "D"]


def test_confidence_coverage_and_stale_propagate() -> None:
    result = traverse(
        [node("A"), node("B", confidence=0.7, source_coverage=("catalog",))],
        [edge("ab", "A", "B", confidence=0.8, source_coverage=("kafka",), evidence_refs=("e:1",), data_status="stale")],
        request(),
    )
    reached = result.paths[1]
    assert reached.confidence == 0.7
    assert reached.source_coverage == ("catalog", "kafka")
    assert reached.evidence_refs == ("e:1",)
    assert reached.data_status == "stale"


@pytest.mark.parametrize(
    "limits,reason",
    [
        ({"max_hops": 1}, "max_hops"),
        ({"max_nodes": 2}, "max_nodes"),
        ({"max_edges": 1}, "max_edges"),
        ({"max_paths": 1}, "max_paths"),
    ],
)
def test_limits_are_reported(limits: dict[str, int], reason: str) -> None:
    result = traverse(
        [node(x) for x in "ABC"], [edge("ab", "A", "B"), edge("ac", "A", "C"), edge("bc", "B", "C")], request(**limits)
    )
    assert result.truncated
    assert reason in str(result.truncation_reason)


def test_duplicate_edges_and_disconnected_nodes() -> None:
    result = traverse([node(x) for x in "ABC"], [edge("ab", "A", "B"), edge("ab", "A", "B")], request())
    assert [p.entity_id for p in result.paths] == ["A", "B"]
    assert not result.truncated


def test_dependency_is_not_degradation() -> None:
    result = traverse([node("A"), node("B")], [edge("ab", "A", "B")], request())
    candidate = result.candidates[1]
    assert candidate.classification == "direct"
    assert candidate.active_anomaly is None
    assert candidate.active_reliability_breach is None


def test_semantic_hash_ignores_confidence_and_order() -> None:
    edges = [edge("ab", "A", "B", confidence=0.1)]
    first = canonical_graph_hash([node("B"), node("A")], edges)
    second = canonical_graph_hash([node("A", confidence=0.2), node("B")], [edge("ab", "A", "B", confidence=0.9)])
    assert first == second
    assert first != canonical_graph_hash([node("A"), node("C")], [edge("ac", "A", "C")])


def test_delta_zero_and_missing_semantics() -> None:
    zero = compare_metric(WindowMetric("throughput", 0, 4, 1), WindowMetric("throughput", 5, 4, 0.8))
    assert zero.absolute_delta == 5
    assert zero.relative_delta is None and zero.reason_code == "zero_baseline"
    missing = compare_metric(WindowMetric("lag", None, 0, 0), WindowMetric("lag", 0, 2, 1))
    assert missing.before_value is None and missing.after_value == 0
    assert not missing.sample_sufficient and missing.reason_code == "missing_value"


def test_hard_limits_rejected() -> None:
    with pytest.raises(ValueError):
        request(max_hops=9)
