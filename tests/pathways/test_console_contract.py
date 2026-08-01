from packages.pathways.intelligence import assemble_pathways, bottlenecks, compare_windows, latency


def edge(edge_id, source, destination, **values):
    return {
        "edge_id": edge_id,
        "source_node_id": source,
        "destination_node_id": destination,
        "tenant_id": "tenant-a",
        "environment": "prod",
        "confidence": values.pop("confidence", 0.8),
        "metrics": values,
        "source_coverage": ["fixture"],
        "evidence_refs": [],
    }


def test_durable_pathway_contains_bounded_topology_and_preserves_zero():
    edges = [edge("e1", "a", "b", latency_ms=0), edge("e2", "b", "c", latency_ms=10)]
    result = assemble_pathways([{"node_id": x} for x in "abc"], edges)[0]
    assert result["edges"][0]["metrics"]["latency_ms"] == 0
    assert [item["node_id"] for item in result["nodes"]] == list("abc")
    assert latency(result["edges"])["p50_ms"] == 0


def test_unavailable_and_estimated_latency_are_explicit():
    assert latency([edge("e", "a", "b")])["method"] == "unavailable"
    assert latency([edge("e", "a", "b", latency_ms=0)])["method"] == "edge_estimate"


def test_bottleneck_wording_is_non_causal_and_zero_is_valid():
    candidates = bottlenecks([edge("e1", "a", "b", latency_ms=0), edge("e2", "b", "c", latency_ms=2)], "latency")
    assert candidates[0]["edge_id"] == "e2"
    assert "not a root-cause claim" in candidates[0]["health_explanation"]


def test_comparison_warning_is_non_causal():
    result = compare_windows(
        {"sample_count": 1, "edge_ids": [], "metrics": {"latency": 0}},
        {"sample_count": 1, "edge_ids": [], "metrics": {"latency": 2}},
    )
    assert result["metric_deltas"]["latency"] == 2
    assert "Correlation does not establish causation" in result["warnings"]
