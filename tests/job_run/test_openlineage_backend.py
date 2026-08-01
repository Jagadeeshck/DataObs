from integrations.airflow.normalizer import normalize_airflow_event
from integrations.dbt.normalizer import normalize_dbt_event
from integrations.spark.normalizer import normalize_spark_event
from src.api.store import InMemoryStore
from src.data_observability.openlineage import OpenLineageValidationError, parse_openlineage_event
from src.data_observability.service import DataObservabilityService, OpenLineageConflictError


def event(kind="START", when="2026-01-01T00:00:00Z", event_id=None):
    value = {
        "eventType": kind,
        "eventTime": when,
        "producer": "https://collector",
        "run": {"runId": "source-1", "facets": {"vendor": {"password": "no", "safe": 1}}},
        "job": {"namespace": "airflow", "name": "orders"},
    }
    if event_id:
        value["eventId"] = event_id
    return value


def test_redaction_limits_and_scoped_ids():
    parsed = parse_openlineage_event(event(), tenant_id="a", environment="prod")
    assert parsed["unknown_facets"]["vendor"]["password"] == "[REDACTED]"
    assert (
        parsed["canonical_run_id"]
        != parse_openlineage_event(event(), tenant_id="b", environment="prod")["canonical_run_id"]
    )
    bad = event()
    bad["job"]["name"] = "x" * 20000
    try:
        parse_openlineage_event(bad)
    except OpenLineageValidationError:
        pass
    else:
        raise AssertionError("oversized string accepted")


def test_lifecycle_duplicate_and_conflict():
    service = DataObservabilityService(InMemoryStore(), "tenant", "prod")
    complete = service.ingest_openlineage_event(event("COMPLETE", "2026-01-01T00:05:00Z"))
    late = service.ingest_openlineage_event(event("START", "2026-01-01T00:00:00Z"))
    assert complete["job_run"]["state"] == late["job_run"]["state"] == "success"
    assert service.ingest_openlineage_event(event("START", "2026-01-01T00:00:00Z"))["deduplicated"]
    service.ingest_openlineage_event(event("RUNNING", event_id="fixed"))
    conflict = event("FAIL", event_id="fixed")
    try:
        service.ingest_openlineage_event(conflict)
    except OpenLineageConflictError:
        pass
    else:
        raise AssertionError("conflicting event identity accepted")


def test_platform_normalisers_are_bounded_and_do_not_retain_compiled_code():
    assert normalize_airflow_event({"dag_id": "d", "dag_run_id": "r", "try_number": 2})["try_number"] == 2
    dbt = normalize_dbt_event({"invocation_id": "i", "unique_id": "model.x", "compiled_sql": "select secret"})
    assert dbt["compiled_code_fingerprint"] and "compiled_sql" not in dbt
    spark = normalize_spark_event({"application_id": "a", "tasks": [{"failed": False}]})
    assert spark["task_summary"]["total"] == 1
