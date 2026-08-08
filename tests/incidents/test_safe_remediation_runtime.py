from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from services.incident_manager.automation.catalogue import CATALOGUE, ActionCatalogue
from services.incident_manager.automation.contracts import ApprovalState, ExecutionResult, ExecutionState
from services.incident_manager.automation.coordinator import AutomationCoordinator, Expired, PolicyDenied
from services.incident_manager.automation.execution import ExecutionWorker, ExecutorRegistry
from services.incident_manager.automation.preview import PreviewService
from services.incident_manager.automation.repository import Conflict, InMemoryAutomationRepository
from services.incident_manager.automation.verification import VerificationEvidence, verify

NOW = datetime(2026, 8, 8, tzinfo=timezone.utc)


def preview(action="rerun_scan", *, actor="requester", provider_ready=False, severity="warning"):
    return PreviewService().create(
        tenant_id="t1",
        environment="prod",
        incident_id="i1",
        incident_revision="7",
        incident_state="investigating",
        severity=severity,
        affected_asset_count=1,
        action_type=action,
        payload={"target_id": "scanner-1", "target_revision": "3"},
        actor=actor,
        request_id="req-1",
        now=NOW,
        provider_ready=provider_ready,
    )


def test_catalogue_and_preview_are_canonical_deterministic_and_fail_closed():
    assert ActionCatalogue().hash == CATALOGUE.hash
    first, second = preview(), preview()
    assert first.preview_id == second.preview_id
    assert first.catalogue_hash == CATALOGUE.hash
    assert first.allowed is False
    assert first.provider_state == "not_configured"
    assert first.risk == "low"
    assert first.previewed_at.isoformat() not in first.preview_id
    with pytest.raises(ValueError, match="allowlisted"):
        preview("shell")
    with pytest.raises(ValidationError):
        PreviewService().create(
            tenant_id="t1",
            environment="prod",
            incident_id="i",
            incident_revision="1",
            incident_state="open",
            severity="warning",
            affected_asset_count=1,
            action_type="rerun_scan",
            payload={"target_id": "x", "target_revision": "1", "url": "https://evil"},
            actor="a",
            request_id="r",
            now=NOW,
        )


def test_risk_escalates_and_critical_suppression_is_denied():
    assert preview(severity="critical").risk == "medium"
    result = preview("suppress_notifications", severity="critical")
    assert result.risk == "high"
    assert result.denial_reason == "critical_suppression_denied"


def test_approval_separation_expiry_occ_and_one_time_consumption():
    repo = InMemoryAutomationRepository()
    coordinator = AutomationCoordinator(repo)
    governed = preview("suppress_notifications")
    coordinator.save_preview(governed)
    approval = coordinator.request_approval(
        governed,
        requester="requester",
        idempotency_key="key",
        reason="bounded reason",
        impact="bounded impact",
        now=NOW,
    )
    assert (
        coordinator.request_approval(
            governed,
            requester="requester",
            idempotency_key="key",
            reason="bounded reason",
            impact="bounded impact",
            now=NOW,
        ).approval_id
        == approval.approval_id
    )
    with pytest.raises(PermissionError):
        coordinator.decide_approval(
            "t1",
            "prod",
            approval.approval_id,
            actor="requester",
            permissions={"workflows:approve"},
            approve=True,
            comment="",
            request_id="r",
            now=NOW,
        )
    with pytest.raises(PermissionError):
        coordinator.decide_approval(
            "t1",
            "prod",
            approval.approval_id,
            actor="other",
            permissions=set(),
            approve=True,
            comment="",
            request_id="r",
            now=NOW,
        )
    approved = coordinator.decide_approval(
        "t1",
        "prod",
        approval.approval_id,
        actor="approver",
        permissions={"workflows:approve"},
        approve=True,
        comment="reviewed",
        request_id="r",
        now=NOW,
    )
    assert approved.state == ApprovalState.APPROVED
    with pytest.raises(Conflict):
        coordinator.decide_approval(
            "t1",
            "prod",
            approval.approval_id,
            actor="another",
            permissions={"workflows:approve"},
            approve=False,
            comment="",
            request_id="r",
            now=NOW,
        )
    expired_preview = governed.model_copy(update={"expires_at": NOW - timedelta(seconds=1)})
    with pytest.raises(Expired):
        coordinator.request_approval(
            expired_preview, requester="x", idempotency_key="x", reason="r", impact="i", now=NOW
        )


def enabled_preview():
    item = preview(provider_ready=True)
    # Catalogue intentionally has no enabled provider. This test models a certified internal adapter while retaining
    # the exact immutable fingerprints produced by the preview contract.
    return item.model_copy(
        update={"allowed": True, "denial_reason": None, "policy_decision": "allowed", "provider_state": "ready"}
    )


def test_execution_idempotency_conflict_claim_fencing_and_verification():
    repo = InMemoryAutomationRepository()
    coordinator = AutomationCoordinator(repo)
    item = enabled_preview()
    first = coordinator.queue_execution(
        item,
        actor="operator",
        idempotency_key="same",
        current_incident_revision="7",
        current_target_revision="3",
        approval_id=None,
        request_id="r",
        now=NOW,
    )
    same = coordinator.queue_execution(
        item,
        actor="operator",
        idempotency_key="same",
        current_incident_revision="7",
        current_target_revision="3",
        approval_id=None,
        request_id="r",
        now=NOW,
    )
    assert same.execution_id == first.execution_id
    different = item.model_copy(update={"preview_id": "other"})
    with pytest.raises(Conflict):
        coordinator.queue_execution(
            different,
            actor="operator",
            idempotency_key="same",
            current_incident_revision="7",
            current_target_revision="3",
            approval_id=None,
            request_id="r",
            now=NOW,
        )

    class Executor:
        action_type = "rerun_scan"
        cancellation_supported = False

        def execute(self, execution):
            return ExecutionResult(True, False, "task-123")

        def lookup(self, execution):
            return ExecutionResult(True, True, "task-123")

        def cancel(self, execution):
            return False

    worker = ExecutionWorker(repo, ExecutorRegistry((Executor(),)), "worker-a")
    claimed = worker.claim(first, NOW)
    with pytest.raises(Conflict):
        ExecutionWorker(repo, ExecutorRegistry((Executor(),)), "worker-b").claim(first, NOW)
    claimed.state = ExecutionState.QUEUED
    repo.update_execution(claimed, claimed.lease_token)
    assert worker.run_once(now=NOW) == 1
    executed = repo.get_execution("t1", "prod", first.execution_id)
    assert executed and executed.state == ExecutionState.VERIFICATION_PENDING
    verified = verify(
        repo,
        executed,
        VerificationEvidence(
            reference="scan-result-1",
            target_id="scanner-1",
            observed_at=NOW + timedelta(seconds=1),
            successful=True,
            recovery_observed=False,
        ),
    )
    assert verified.state == ExecutionState.VERIFIED
    assert verified.operation_reference == "task-123"


def test_stale_revision_and_unconfigured_execution_are_exact_failures():
    coordinator = AutomationCoordinator(InMemoryAutomationRepository())
    with pytest.raises(PolicyDenied, match="not configured"):
        coordinator.queue_execution(
            preview(),
            actor="operator",
            idempotency_key="x",
            current_incident_revision="7",
            current_target_revision="3",
            approval_id=None,
            request_id="r",
            now=NOW,
        )
    with pytest.raises(Conflict, match="revision"):
        coordinator.queue_execution(
            enabled_preview(),
            actor="operator",
            idempotency_key="x",
            current_incident_revision="8",
            current_target_revision="3",
            approval_id=None,
            request_id="r",
            now=NOW,
        )
