from dataclasses import replace

import pytest

from integrations.dbt import DbtArtifactEnvelope, DbtArtifactError, parse_artifact
from integrations.dbt.safety import ArtifactLimits
from services.change_gates.changed_models import parse_manifest as gate_parse_manifest
from services.dbt_intelligence.health import project_health
from services.dbt_intelligence.lineage_projection import declared_edges, reconcile_lineage
from services.dbt_intelligence.repository import MemoryDbtIntelligenceRepository
from services.dbt_intelligence.service import DbtIntelligenceService
from services.dbt_intelligence.test_intelligence import evaluate_test_history


def envelope(kind="manifest"):
    return DbtArtifactEnvelope("tenant-a", "prod", "jaffle", "Jaffle", kind, "", "")


def manifest(**extra):
    value = {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12/manifest.json",
            "dbt_version": "1.10.0",
            "invocation_id": "inv-1",
        },
        "nodes": {
            "model.pkg.orders": {
                "resource_type": "model",
                "name": "orders",
                "package_name": "pkg",
                "database": "warehouse",
                "schema": "analytics",
                "config": {"materialized": "incremental", "contract": {"enforced": True}},
                "columns": {"id": {"data_type": "integer"}},
                "depends_on": {"nodes": ["source.pkg.raw.orders"]},
            },
            "test.pkg.not_null_orders_id": {
                "resource_type": "test",
                "name": "not_null_orders_id",
                "depends_on": {"nodes": ["model.pkg.orders"]},
            },
        },
        "sources": {
            "source.pkg.raw.orders": {
                "resource_type": "source",
                "name": "orders",
                "source_name": "raw",
                "columns": {"id": {"data_type": "integer"}},
            }
        },
        "semantic_models": {
            "semantic_model.pkg.orders": {
                "resource_type": "semantic_model",
                "name": "orders",
                "depends_on": {"nodes": ["model.pkg.orders"]},
                "entities": [{"name": "order", "type": "primary"}],
            }
        },
        "metrics": {
            "metric.pkg.revenue": {
                "resource_type": "metric",
                "name": "revenue",
                "depends_on": {"nodes": ["semantic_model.pkg.orders"]},
            }
        },
        "saved_queries": {
            "saved_query.pkg.exec": {
                "resource_type": "saved_query",
                "name": "exec",
                "depends_on": {"nodes": ["metric.pkg.revenue"]},
            }
        },
        "exposures": {
            "exposure.pkg.dashboard": {
                "resource_type": "exposure",
                "name": "dashboard",
                "depends_on": {"nodes": ["model.pkg.orders"]},
            }
        },
        "groups": {"group.pkg.finance": {"resource_type": "group", "name": "finance"}},
        "unit_tests": {
            "unit_test.pkg.orders": {
                "resource_type": "unit_test",
                "name": "orders",
                "depends_on": {"nodes": ["model.pkg.orders"]},
            }
        },
    }
    value.update(extra)
    return value


def test_manifest_resource_families_and_canonical_identity():
    result = parse_artifact(manifest(), envelope())
    assert {item["resource_type"] for item in result.resources} == {
        "model",
        "source",
        "test",
        "semantic_model",
        "metric",
        "saved_query",
        "exposure",
        "group",
        "unit_test",
    }
    model = next(item for item in result.resources if item["resource_type"] == "model")
    assert model["asset_id"].startswith("dbt_") and model["contract"]["enabled"] is True
    assert "compiled_sql" not in repr(result)


@pytest.mark.parametrize(
    "field", ["raw_sql", "compiled_sql", "raw_code", "compiled_code", "environment", "token", "private_key", "rows"]
)
def test_unsafe_artifact_fields_are_rejected(field):
    value = manifest()
    value["nodes"]["model.pkg.orders"][field] = "SECRET sentinel"
    with pytest.raises(DbtArtifactError) as error:
        parse_artifact(value, envelope())
    assert error.value.code == "unsafe_field_detected" and "SECRET sentinel" not in str(error.value)


def test_unknown_and_malformed_schema_fail_before_partial_parsing():
    value = manifest()
    value["metadata"]["dbt_schema_version"] = "https://schemas.getdbt.com/dbt/manifest/v99/manifest.json"
    with pytest.raises(DbtArtifactError) as error:
        parse_artifact(value, envelope())
    assert error.value.code == "unsupported_schema_version"
    value["metadata"]["dbt_schema_version"] = "manifest-v12"
    with pytest.raises(DbtArtifactError) as error:
        parse_artifact(value, envelope())
    assert error.value.code == "invalid_artifact"


def test_limits_are_enforced():
    with pytest.raises(DbtArtifactError) as error:
        parse_artifact(manifest(), envelope(), ArtifactLimits(max_resources=1))
    assert error.value.code == "resource_limit_exceeded"
    with pytest.raises(DbtArtifactError) as error:
        parse_artifact(manifest(), envelope(), ArtifactLimits(max_bytes=10))
    assert error.value.code == "artifact_too_large"


@pytest.mark.parametrize(
    "kind,uri,key",
    [
        ("run_results", "https://schemas.getdbt.com/dbt/run-results/v6/run-results.json", "executions"),
        ("catalog", "https://schemas.getdbt.com/dbt/catalog/v1/catalog.json", "catalog"),
        ("freshness", "https://schemas.getdbt.com/dbt/sources/v3/sources.json", "freshness"),
    ],
)
def test_other_artifact_families(kind, uri, key):
    document = {
        "metadata": {"dbt_schema_version": uri, "dbt_version": "1.10.0", "invocation_id": "inv"},
        "results": [{"unique_id": "test.pkg.x", "status": "skipped", "message": "select secret from private"}],
    }
    if kind == "catalog":
        document = {
            "metadata": document["metadata"],
            "nodes": {
                "model.pkg.x": {
                    "columns": {"id": {"index": 1, "type": "INT"}},
                    "stats": {"row_count": {"value": 0}, "unknown": {"value": "secret"}},
                }
            },
        }
    result = parse_artifact(document, replace(envelope(), artifact_type=kind))
    assert result.envelope.artifact_schema_version
    assert "select secret" not in repr(result)
    assert getattr(result, key)


def test_flaky_consistent_and_missing_semantics():
    flaky = evaluate_test_history([{"status": item} for item in ["pass", "pass", "fail", "pass", "fail", "pass"]])
    assert flaky["health_state"] == "flaky_candidate"
    assert evaluate_test_history([{"status": "fail"}] * 6)["health_state"] == "consistently_failing"
    assert evaluate_test_history([])["health_state"] == "never_observed"
    assert evaluate_test_history([{"status": "skipped"}])["health_state"] == "unknown"


def test_lineage_is_bounded_and_reconciled_without_deleting_provenance():
    resources = list(parse_artifact(manifest(), envelope()).resources)
    edges = declared_edges(resources)
    pair = edges[0]
    reconciled = reconcile_lineage(
        edges, [{"source": pair["source"], "target": pair["target"]}, {"source": "x", "target": "y"}]
    )
    assert {item["state"] for item in reconciled} >= {"declared_and_observed", "declared_only", "observed_only"}


def test_health_excludes_missing_components():
    assert project_health({})["health_state"] == "unknown"
    result = project_health({"run_reliability": 100})
    assert result["health_score"] == 100 and result["health_state"] == "partial" and result["confidence"] == 0.3


def test_idempotent_ingestion_and_tenant_isolation():
    repository = MemoryDbtIntelligenceRepository()
    service = DbtIntelligenceService(repository)
    assert service.ingest("a", "prod", "p", "P", "manifest", manifest())["status"] == "created"
    assert service.ingest("a", "prod", "p", "P", "manifest", manifest())["status"] == "replayed"
    service.ingest("b", "prod", "p", "P", "manifest", manifest())
    assert len(repository.list_projects("a", "prod")) == len(repository.list_projects("b", "prod")) == 1
    assert repository.list_projects("a", "dev") == []


def test_change_gate_parser_is_thin_canonical_compatibility():
    assert list(gate_parse_manifest(manifest())) == ["model.pkg.orders"]
