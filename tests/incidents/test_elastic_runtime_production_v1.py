from datetime import datetime, timedelta, timezone

from services.incident_manager.automation.contracts import Execution, ExecutionState
from services.incident_manager.automation.repository import Conflict, InMemoryAutomationRepository
from services.incident_manager.automation.targets import ActionTarget, BoundedActionTargetResolver


class Sources:
    def relevant_finding_references(self, tenant_id, environment, incident_id, limit):
        return ["finding-1"]

    def get_finding(self, tenant_id, environment, reference):
        return {"scanner_id": "scanner-1"}

    def get_target(self, tenant_id, environment, target_type, target_id):
        return ActionTarget(target_type, target_id, "owner-revision-7")


def test_normal_incident_resolves_scanner_target() -> None:
    source = Sources()
    result = BoundedActionTargetResolver(source, source, source).resolve(
        tenant_id="tenant", environment="prod", incident_id="incident", action_type="rerun_scan"
    )
    assert result.status == "resolved"
    assert result.target == ActionTarget("scanner", "scanner-1", "owner-revision-7")


def test_target_revision_loaded_from_owner_repository() -> None:
    source = Sources()
    resolver = BoundedActionTargetResolver(source, source, source)
    assert (
        resolver.reload(
            tenant_id="tenant", environment="prod", target=ActionTarget("scanner", "scanner-1", "stale")
        ).revision
        == "owner-revision-7"
    )


def test_heartbeat_renewal_is_fenced_by_owner() -> None:
    now = datetime.now(timezone.utc)
    execution = Execution(
        execution_id="exec",
        tenant_id="tenant",
        environment="prod",
        incident_id="incident",
        action_type="rerun_scan",
        state=ExecutionState.RUNNING,
        request_id="request",
        actor="actor",
        action_fingerprint="fingerprint",
        catalogue_hash="catalogue",
        policy_hash="policy",
        incident_revision="1",
        preview_id="preview",
        approval_id=None,
        payload_fingerprint="payload",
        target={"type": "scanner", "id": "scanner", "revision": "1"},
        lease_owner="worker-a",
        lease_token=2,
        lease_expires_at=now,
        created_at=now,
        updated_at=now,
        timeout_seconds=30,
        max_attempts=1,
    )
    repo = InMemoryAutomationRepository()
    repo.executions[execution.execution_id] = execution
    renewed = repo.renew_execution_lease("tenant", "prod", "exec", "worker-a", 2, now + timedelta(seconds=30))
    assert renewed.lease_expires_at > now
    try:
        repo.renew_execution_lease("tenant", "prod", "exec", "worker-old", 1, now + timedelta(seconds=60))
    except Conflict:
        pass
    else:
        raise AssertionError("stale worker renewed a fenced lease")
