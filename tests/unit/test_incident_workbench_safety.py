from datetime import datetime, timedelta, timezone

import pytest

from integrations.elastic.workflows.validator import validate_pack, validate_workflow
from packages.domain_model.incident import Incident, IncidentState
from services.action_executor.catalogue import ActionCatalogue
from services.approvals.repository import InMemoryApprovalRepository
from services.approvals.service import ApprovalRequest, ApprovalService, ApprovalStatus
from services.incident_manager.lifecycle import transition


def incident(state: IncidentState = IncidentState.OPEN) -> Incident:
    return Incident(
        id="i1", tenant_id="t1", environment="prod", title="Failure", incident_state=state, deduplication_key="d1"
    )


def test_public_lifecycle_can_resolve_and_requires_resolution_reason():
    assert transition(incident(), IncidentState.RESOLVED, reason="fixed").resolved_at is not None
    item = incident(IncidentState.MONITORING_RECOVERY)
    with pytest.raises(ValueError, match="reason"):
        transition(item, IncidentState.RESOLVED)
    assert transition(item, IncidentState.RESOLVED, reason="all findings recovered").closed_at is None


def test_action_catalogue_is_deny_by_default_and_preview_is_server_owned():
    catalogue = ActionCatalogue()
    preview = catalogue.preview("rerun_airflow", target="dag:daily", current_state="failed")
    assert preview["approval_required"] is True
    assert preview["verification_plan"] == "rerun_succeeded"
    with pytest.raises(ValueError, match="not allowlisted"):
        catalogue.preview("shell", target="host", current_state="unknown")


def test_approval_requires_existing_request_and_separation_of_duties():
    repository = InMemoryApprovalRepository()
    service = ApprovalService(repository)
    with pytest.raises(KeyError):
        service.decide(
            "t1",
            "missing",
            actor="operator",
            scopes=["approvals:decide"],
            decision=ApprovalStatus.APPROVED,
            comment="ok",
        )
    repository.save(
        ApprovalRequest(
            id="a1",
            tenant_id="t1",
            environment="prod",
            action_id="x1",
            requester="requester",
            policy_version="v1",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    with pytest.raises(PermissionError, match="own"):
        service.decide(
            "t1", "a1", actor="requester", scopes=["approvals:decide"], decision=ApprovalStatus.APPROVED, comment="self"
        )


def test_workflow_rejects_unsafe_steps(tmp_path):
    workflow = tmp_path / "bad.yaml"
    workflow.write_text("id: bad\nsteps:\n  - type: kibana.request\n")
    with pytest.raises(ValueError, match="deprecated"):
        validate_workflow(workflow)


def test_bundled_workflows_are_allowlisted():
    assert len(validate_pack()) == 6


def test_workflow_rejects_sql_but_permits_esql(tmp_path):
    unsafe = tmp_path / "sql.yaml"
    unsafe.write_text("id: bad\nsteps:\n  - type: sql.query\n")
    with pytest.raises(ValueError, match="forbidden"):
        validate_workflow(unsafe)
    safe = tmp_path / "esql.yaml"
    safe.write_text("id: good\nsteps:\n  - type: elasticsearch.esql\n  - type: waitForInput\n")
    assert validate_workflow(safe)["id"] == "good"
