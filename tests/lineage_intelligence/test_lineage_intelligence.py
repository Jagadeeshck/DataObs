from services.lineage_intelligence.impact import analyse, score
from services.lineage_intelligence.models import ImpactRequest, LineageEdge, SchemaColumn, SchemaVersion
from services.lineage_intelligence.repository import MemoryLineageRepository
from services.lineage_intelligence.schema_diff import compare_schemas
from services.lineage_intelligence.traversal import traverse


def edge(a: str, b: str, **kwargs):
    return LineageEdge.create(a, b, relationship_type="direct", confidence=0.9, **kwargs)


def repository(*edges):
    repo = MemoryLineageRepository()
    for item in edges:
        repo.add_edge("t", "prod", item)
    return repo


def test_deterministic_edge_ids_distinguish_columns():
    assert edge("a", "b").edge_id == edge("a", "b").edge_id
    assert edge("a", "b", level="column", source_column="x", target_column="y").edge_id != edge("a", "b").edge_id


def test_bounded_both_direction_cycle_and_tenant_isolation():
    repo = repository(edge("a", "b"), edge("b", "c"), edge("c", "a"))
    repo.add_edge("other", "prod", edge("a", "secret"))
    result = traverse(repo, "t", "prod", ImpactRequest("b", direction="both", max_depth=5, max_nodes=10, max_edges=10))
    assert {n["asset_id"] for n in result.nodes} == {"a", "b", "c"}
    assert result.cycles
    assert "secret" not in str(result)


def test_high_fanout_is_explicitly_truncated():
    repo = repository(*(edge("root", f"n{i}") for i in range(20)))
    result = traverse(repo, "t", "prod", ImpactRequest("root", max_nodes=5, max_edges=5))
    assert result.truncated
    assert result.warnings


def test_stale_and_as_of_filters():
    repo = repository(edge("a", "b", stale=True), edge("a", "c", observed_at="2025-02-01T00:00:00Z"))
    request = ImpactRequest("a", as_of="2025-01-01T00:00:00Z")
    assert len(traverse(repo, "t", "prod", request).edges) == 0
    assert len(traverse(repo, "t", "prod", ImpactRequest("a", include_stale_edges=True)).edges) == 2


def version(columns, partitions=()):
    return SchemaVersion("asset", "2026-01-01T00:00:00Z", "openlineage", tuple(columns), tuple(partitions))


def test_schema_fingerprint_and_breaking_drop():
    old = version([SchemaColumn("id", "integer", False), SchemaColumn("name", "string", True)])
    new = version([SchemaColumn("id", "integer", False)])
    assert old.fingerprint == old.fingerprint
    change = compare_schemas(old, new)
    assert change["change_type"] == "breaking"
    assert "column_removed" in change["reason_codes"]


def test_schema_widen_narrow_nullability_partition_and_rename_candidate():
    widened = compare_schemas(
        version([SchemaColumn("x", "integer", True)]), version([SchemaColumn("x", "bigint", True)])
    )
    assert widened["change_type"] == "compatible"
    narrow = compare_schemas(
        version([SchemaColumn("x", "bigint", True)]), version([SchemaColumn("x", "integer", False)])
    )
    assert narrow["change_type"] == "potentially_breaking"
    partition = compare_schemas(
        version([SchemaColumn("old", "string", True)], ("old",)),
        version([SchemaColumn("new", "string", True)], ("new",)),
    )
    assert partition["change_type"] == "breaking"
    assert partition["rename_candidates"][0]["relationship"] == "inferred"


def test_unknown_provider_type_is_not_compatible():
    result = compare_schemas(version([SchemaColumn("x", "vendor_a")]), version([SchemaColumn("x", "vendor_b")]))
    assert result["change_type"] == "unknown"
    assert "provider_type_unknown" in result["reason_codes"]


def test_score_excludes_missing_but_retains_measured_zero():
    result = score({"change_severity": 0.0, "path_confidence": None})
    assert result["impact_score"] == 0
    assert result["normalized_weights"] == {"change_severity": 1.0}


def test_impact_is_idempotent_and_separates_confidence():
    repo = repository(edge("a", "b"), edge("b", "c"))
    request = ImpactRequest("a")
    first = analyse(repo, "t", "prod", request, {"severity": "high"})
    second = analyse(repo, "t", "prod", request, {"severity": "high"})
    assert first["analysis_id"] == second["analysis_id"]
    assert first["directly_affected_count"] == 1
    assert first["transitively_affected_count"] == 1
    assert first["affected_assets"][0]["confidence"] == 0.9
