from datetime import datetime, timezone

from integrations.dbt.artifacts.run_results import parse
from packages.elastic_store.manifest import migrations
from services.job_observer.actions import validate_action
from services.job_observer.critical_path import calculate
from services.job_observer.service import canonical_job_id
from services.openlineage_ingest.authentication import SourceBinding
from services.openlineage_ingest.normalizer import normalize
from services.openlineage_ingest.ordering import resolve
from services.spark_observer.skew import detect


def event(kind="START"):
    return {
        "eventType": kind,
        "eventTime": "2026-01-01T00:00:00Z",
        "run": {"runId": "r1", "facets": {"vendor": {"x": 1}}},
        "job": {"namespace": "n", "name": "j"},
    }


def test_migration_is_forward_only_and_complete():
    m = migrations()[-1]
    assert m.migration_id == "0008_job_run_observability"
    assert m.dependencies == ["0007_automated_monitoring_data_products_rca"]
    assert len(m.operations["mutable_indices"]) == 15


def test_openlineage_unknown_facets_and_tenant_binding():
    x = normalize(event(), SourceBinding("airflow", "tenant-a", "prod"))
    assert x["tenant_id"] == "tenant-a"
    assert x["openlineage_facets"]["run"]["vendor"]["x"] == 1


def test_event_idempotency_and_ordering():
    b = SourceBinding("airflow", "t", "p")
    assert normalize(event(), b)["event_id"] == normalize(event(), b)["event_id"]
    now = datetime.now(timezone.utc)
    assert resolve(("COMPLETE", now), ("START", now))[0] == "COMPLETE"


def test_identity_is_tenant_scoped():
    assert canonical_job_id("a", "prod", "airflow", "n", "x") != canonical_job_id("b", "prod", "airflow", "n", "x")


def test_critical_path():
    assert calculate([{"id": "a", "duration_ms": 10}, {"id": "b", "duration_ms": 20, "dependencies": ["a"]}])[
        "segments"
    ] == ["a", "b"]


def test_safe_action_allowlist():
    assert validate_action("trigger_airflow_dag", {"logical_date": "x"}, {"logical_date"})
    try:
        validate_action("trigger_airflow_dag", {"shell": "rm"}, {"logical_date"})
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe parameter accepted")


def test_dbt_compiled_sql_never_returned():
    out = parse({"results": [{"unique_id": "model.x", "compiled_code": "select secret from x"}]})
    assert "compiled_code" not in out["results"][0]
    assert out["results"][0]["compiled_code_fingerprint"]


def test_skew_requires_evidence():
    assert not detect([{"duration_ms": 100}])["skew"]
    assert detect([{"duration_ms": 10}] * 5 + [{"duration_ms": 100}])["skew"]
