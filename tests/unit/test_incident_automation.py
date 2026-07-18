from datetime import datetime, timezone

from packages.domain_model.incident import Finding, FindingType, Severity, SignalType
from packages.domain_model.workflow import WorkflowExecution, WorkflowExecutionStatus, WorkflowTriggerType
from services.incident_manager import IncidentManagerService


def test_finding_deterministic_id_and_serialization():
    kwargs = dict(
        tenant_id="t1",
        environment="prod",
        finding_type=FindingType.SCHEMA_CHANGE,
        signal_type=SignalType.POSTGRES_SCHEMA_CHANGE,
        source_event_id="evt-1",
        asset_id="db.schema.table",
        title="Breaking change",
        summary="Column removed",
        severity=Severity.HIGH,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
    )
    assert Finding(**kwargs).id == Finding(**kwargs).id


def test_duplicate_findings_create_one_incident():
    svc = IncidentManagerService()
    event = {
        "id": "evt-1",
        "event_type": "schema_change",
        "tenant_id": "t1",
        "environment": "prod",
        "asset_id": "a",
        "severity": "critical",
    }
    first = svc.ingest(event, tenant_id="t1")
    second = svc.ingest(event, tenant_id="t1")
    assert first["incident"]["id"] == second["incident"]["id"]
    assert second["incident"]["occurrence_count"] == 2


def test_cross_tenant_rejected():
    svc = IncidentManagerService()
    try:
        svc.ingest({"id": "evt-1", "tenant_id": "other"}, tenant_id="t1")
    except ValueError as exc:
        assert "cross-tenant" in str(exc)
    else:
        raise AssertionError("cross tenant event accepted")


def test_workflow_terminal_status_contract():
    execution = WorkflowExecution(
        id="exec-1",
        tenant_id="t1",
        workflow_id="wf",
        trigger=WorkflowTriggerType.MANUAL,
        workflow_status=WorkflowExecutionStatus.COMPLETED,
    )
    assert execution.model_dump(mode="json")["workflow_status"] == "completed"
