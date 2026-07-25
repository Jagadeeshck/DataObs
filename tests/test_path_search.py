from datetime import datetime, timezone

from packages.domain_model.investigation import PathwayEvidence, PathwayRouteEdge, PathwayRouteNode
from services.product_query.path_search import search_paths


def edge(identifier: str, source: str, target: str, confidence: float = 1.0):
    return PathwayRouteEdge(
        id=identifier,
        source_node_id=source,
        destination_node_id=target,
        evidence=PathwayEvidence(
            evidence_type="trace_observed",
            confidence=confidence,
            observed_at=datetime.now(timezone.utc),
            coverage="complete",
        ),
    )


def test_search_is_bounded_cycle_safe_and_deterministic():
    nodes = [PathwayRouteNode(id=value, name=value, node_type="dataset") for value in "ABCD"]
    edges = [
        edge("ab", "A", "B"),
        edge("bd", "B", "D"),
        edge("ac", "A", "C", 0.8),
        edge("cd", "C", "D"),
        edge("ba", "B", "A"),
    ]
    first = search_paths(nodes, edges, "A", "D", max_hops=3, max_paths=10)
    second = search_paths(nodes, edges, "A", "D", max_hops=3, max_paths=10)
    assert [route.id for route in first[0]] == [route.id for route in second[0]]
    assert len(first[0]) == 2
    assert all(len(route.edges) <= 3 for route in first[0])
    assert first[0][0].ranking_explanation["evidence_confidence"] == 1


def test_search_reports_partial_and_filters_low_confidence():
    nodes = [PathwayRouteNode(id=value, name=value, node_type="dataset") for value in "ABC"]
    routes, partial, excluded, _ = search_paths(
        nodes,
        [edge("ab", "A", "B", 0.3), edge("bc", "B", "C")],
        "A",
        "C",
        max_hops=2,
        max_paths=2,
        minimum_confidence=0.5,
    )
    assert not routes
    assert not partial
    assert excluded == 1
