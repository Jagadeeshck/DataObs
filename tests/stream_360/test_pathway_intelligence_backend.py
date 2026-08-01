from packages.pathways.intelligence import (
    assemble_pathways,
    bottlenecks,
    canonical_edge,
    canonical_node,
    compare_windows,
    confidence_for,
    latency,
    pathway_health,
)
from services.pathway_worker.checkpoint_store import EventWatermark


def graph():
    nodes = [
        canonical_node("t", "prod", kind, name)
        for kind, name in [("service", "producer"), ("kafka_topic", "orders"), ("service", "consumer")]
    ]
    edges = [
        canonical_edge(
            "t",
            "prod",
            nodes[0]["node_id"],
            nodes[1]["node_id"],
            "producer_to_topic",
            evidence_type="trace_observed",
            evidence_refs=["a"],
        ),
        canonical_edge(
            "t",
            "prod",
            nodes[1]["node_id"],
            nodes[2]["node_id"],
            "topic_to_consumer",
            evidence_type="trace_observed",
            evidence_refs=["b"],
        ),
    ]
    return nodes, edges


def test_watermark_commits_event_not_wall_clock():
    result = EventWatermark("t", "prod").committed("2026-01-01T00:00:00+00:00", "span-2", 2, "worker", 4)
    assert result.position() == ["2026-01-01T00:00:00+00:00", "span-2"]
    assert result.documents_processed == 2 and result.fencing_token == 4


def test_identity_is_tenant_environment_scoped_and_evidence_precedence():
    first = canonical_node("t", "prod", "service", "orders")
    assert first["node_id"] == canonical_node("t", "prod", "service", "orders")["node_id"]
    assert first["node_id"] != canonical_node("other", "prod", "service", "orders")["node_id"]
    assert confidence_for(["trace_observed"]) > confidence_for(["inferred"])


def test_complete_partial_cycle_and_truncation():
    nodes, edges = graph()
    complete = assemble_pathways(nodes, edges)
    assert complete[0]["classification"] == "complete" and not complete[0]["truncated"]
    partial = edges[:1] + [
        canonical_edge("t", "prod", nodes[1]["node_id"], nodes[2]["node_id"], "partial_edge", evidence_type="unknown")
    ]
    assert assemble_pathways(nodes, partial)[0]["classification"] == "partial"
    cycle = edges + [
        canonical_edge(
            "t", "prod", nodes[2]["node_id"], nodes[0]["node_id"], "topic_to_consumer", evidence_type="structural"
        )
    ]
    assert any(item["truncated"] for item in assemble_pathways(nodes, cycle))
    assert assemble_pathways(nodes, edges, max_hops=1)[0]["truncated"]


def test_health_latency_and_bottlenecks_are_explainable():
    _, edges = graph()
    edges[0] |= {"health": "critical", "metrics": {"latency_ms": 90, "lag_messages": 10}}
    edges[1] |= {"health": "unknown", "metrics": {"latency_ms": 10, "lag_messages": 30}}
    assert pathway_health(edges)["health"] == "critical"
    assert latency(edges)["method"] == "edge_estimate"
    candidates = bottlenecks(edges, "latency")
    assert candidates[0]["contribution_percentage"] == 90
    assert "not a root-cause" in candidates[0]["health_explanation"]
    assert bottlenecks([{**edges[0], "metrics": {"latency_ms": 0}}], "latency") == []


def test_trace_latency_and_safe_comparison():
    _, edges = graph()
    edges[0]["metrics"] = {
        "end_to_end_latency": {"correlation_id": "trace", "p50_ms": 4, "p95_ms": 9, "p99_ms": 12, "sample_count": 3}
    }
    assert latency(edges)["method"] == "trace_derived"
    comparison = compare_windows(
        {"edge_ids": ["a"], "metrics": {"lag": 3}, "sample_count": 1},
        {"edge_ids": ["b"], "metrics": {"lag": 5}, "sample_count": 2},
    )
    assert comparison["metric_deltas"]["lag"] == 2
    assert comparison["new_edges"] == ["b"] and comparison["removed_edges"] == ["a"]
    assert "causation" in comparison["warnings"][0]
