from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from services.incident_manager.automation.contracts import ApprovalState, ExecutionResult, ExecutionState
from services.incident_manager.automation.coordinator import AutomationCoordinator, Expired
from services.incident_manager.automation.execution import (
    ExecutionWorker,
    ExecutorRegistry,
    ProviderOutcomeUnknown,
    RetryableBeforeSubmission,
)
from services.incident_manager.automation.preview import PreviewService
from services.incident_manager.automation.reconciliation import AutomationReconciler
from services.incident_manager.automation.repository import Conflict, InMemoryAutomationRepository
from services.incident_manager.automation.verification import VerificationEvidence, verify

NOW = datetime(2026, 8, 8, tzinfo=timezone.utc)


def make_preview(*, action="rerun_scan", actor="operator", now=NOW, assets=1, state="investigating"):
    item = PreviewService().create(
        tenant_id="tenant-a",
        environment="production",
        incident_id="incident-1",
        incident_revision="7",
        incident_state=state,
        severity="warning",
        affected_asset_count=assets,
        action_type=action,
        payload={"target_id": "scanner-real", "target_revision": "scanner-rev-3"},
        actor=actor,
        request_id="request-preview",
        now=now,
        provider_ready=True,
    )
    return item.model_copy(
        update={"allowed": True, "denial_reason": None, "policy_decision": "allowed", "provider_state": "ready"}
    )


def approve(repo, item):
    coordinator = AutomationCoordinator(repo)
    saved = coordinator.save_preview(item)
    approval = coordinator.request_approval(
        saved, requester=item.actor, idempotency_key="approval-key", reason="routine change", impact="bounded", now=NOW
    )
    return coordinator.decide_approval(
        item.tenant_id,
        item.environment,
        approval.approval_id,
        actor="approver",
        permissions={"workflows:approve"},
        approve=True,
        comment="reviewed",
        request_id="decision-1",
        now=NOW,
    )


def queue(repo, item, approval_id=None, key="key"):
    return AutomationCoordinator(repo).queue_execution(
        item,
        actor=item.actor,
        idempotency_key=key,
        current_incident_revision=item.incident_revision,
        current_target_revision=item.target["revision"],
        approval_id=approval_id,
        request_id=f"queue-{key}",
        now=NOW,
    )


def test_one_approval_cannot_publish_two_executions():
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    approval = approve(repo, item)

    def attempt(key):
        try:
            return queue(repo, item, approval.approval_id, key).execution_id
        except (Conflict, PermissionError):
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ("one", "two")))
    assert len(repo.executions) == 1
    assert len({value for value in results if value}) == 1
    assert repo.approvals[approval.approval_id].state == ApprovalState.CONSUMED


def test_reserved_approval_recovers_after_crash():
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    approval = approve(repo, item)
    approval.state = ApprovalState.RESERVED
    approval.reserved_execution_id = "exe_never_published"
    approval.reserved_by = item.actor
    approval.reserved_at = NOW
    approval.reservation_expires_at = NOW + timedelta(seconds=1)
    repo.approvals[approval.approval_id] = approval
    assert AutomationReconciler(repo).run_once(now=NOW + timedelta(seconds=2)) == 1
    assert repo.approvals[approval.approval_id].state == ApprovalState.APPROVED


def test_execution_creation_reconciles_reserved_approval():
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    approval = approve(repo, item)
    execution = queue(repo, item, approval.approval_id)
    stored = repo.approvals[approval.approval_id]
    stored.state = ApprovalState.RESERVED
    stored.reserved_execution_id = execution.execution_id
    repo.approvals[approval.approval_id] = stored
    assert AutomationReconciler(repo).run_once(now=NOW) == 1
    assert repo.approvals[approval.approval_id].state == ApprovalState.CONSUMED


class RaisingExecutor:
    action_type = "rerun_scan"
    cancellation_supported = False

    def __init__(self, error):
        self.error = error
        self.calls = 0

    def execute(self, execution):
        self.calls += 1
        raise self.error

    def lookup(self, execution):
        return ExecutionResult(True, True, "provider-op")

    def cancel(self, execution):
        return False


def test_executor_exception_does_not_kill_worker():
    repo = InMemoryAutomationRepository()
    first = queue(repo, make_preview(), key="one")
    second = queue(repo, make_preview(), key="two")
    executor = RaisingExecutor(RuntimeError("secret provider detail"))
    assert ExecutionWorker(repo, ExecutorRegistry((executor,)), "worker").run_once(limit=2, now=NOW) == 2
    assert executor.calls == 2
    assert {repo.executions[first.execution_id].state, repo.executions[second.execution_id].state} == {
        ExecutionState.RECONCILIATION_REQUIRED
    }
    assert "secret" not in str(repo.executions.values())


def test_uncertain_provider_outcome_is_not_blindly_retried():
    repo = InMemoryAutomationRepository()
    execution = queue(repo, make_preview())
    executor = RaisingExecutor(ProviderOutcomeUnknown())
    ExecutionWorker(repo, ExecutorRegistry((executor,)), "worker").run_once(now=NOW)
    assert repo.executions[execution.execution_id].state == ExecutionState.RECONCILIATION_REQUIRED
    assert executor.calls == 1


def test_retryable_before_submission_keeps_same_execution_identity():
    repo = InMemoryAutomationRepository()
    execution = queue(repo, make_preview())
    ExecutionWorker(repo, ExecutorRegistry((RaisingExecutor(RetryableBeforeSubmission()),)), "worker").run_once(now=NOW)
    stored = repo.executions[execution.execution_id]
    assert stored.state == ExecutionState.QUEUED
    assert stored.execution_id == execution.execution_id


def test_expired_running_lease_is_recoverable():
    repo = InMemoryAutomationRepository()
    execution = queue(repo, make_preview())
    execution.state = ExecutionState.RUNNING
    execution.execution_started_at = NOW
    execution.lease_token = 1
    execution.lease_expires_at = NOW
    repo.executions[execution.execution_id] = execution
    executor = RaisingExecutor(RuntimeError())
    assert ExecutionWorker(repo, ExecutorRegistry((executor,)), "new-worker").recover_expired(now=NOW) == 1
    assert repo.executions[execution.execution_id].state == ExecutionState.VERIFICATION_PENDING


def test_old_fencing_token_cannot_update_execution():
    repo = InMemoryAutomationRepository()
    execution = queue(repo, make_preview())
    old = execution.model_copy(deep=True)
    execution.lease_token += 1
    repo.update_execution(execution, 0)
    old.state = ExecutionState.FAILED
    with pytest.raises(Conflict):
        repo.update_execution(old, 0)


@pytest.mark.parametrize(
    ("state", "allowed"),
    [
        ("open", True),
        ("acknowledged", True),
        ("investigating", True),
        ("monitoring", True),
        ("resolved", False),
        ("closed", False),
        ("new", False),
    ],
)
def test_required_incident_states_are_enforced(state, allowed):
    item = PreviewService().create(
        tenant_id="t",
        environment="dev",
        incident_id="i",
        incident_revision="1",
        incident_state=state,
        severity="warning",
        affected_asset_count=1,
        action_type="rerun_scan",
        payload={"target_id": "scanner", "target_revision": "2"},
        actor="a",
        request_id="r",
        now=NOW,
        provider_ready=True,
    )
    if allowed:
        assert item.denial_reason == "executor_not_configured"
    else:
        assert item.denial_reason in {"incident_state_disallowed", "incident_state_not_allowed"}


@pytest.mark.parametrize(("count", "risk"), [(0, "low"), (1, "low"), (25, "low"), (26, "medium"), (10000, "medium")])
def test_full_asset_count_escalates_risk(count, risk):
    assert make_preview(assets=count).risk == risk


def test_identical_live_preview_returns_durable_instance():
    repo = InMemoryAutomationRepository()
    coordinator = AutomationCoordinator(repo)
    first = coordinator.save_preview(make_preview(now=NOW))
    second = coordinator.save_preview(make_preview(now=NOW + timedelta(minutes=1)))
    assert second == first


def test_expired_preview_creates_next_generation():
    repo = InMemoryAutomationRepository()
    coordinator = AutomationCoordinator(repo)
    first = coordinator.save_preview(make_preview(now=NOW))
    second = coordinator.save_preview(make_preview(now=NOW + timedelta(minutes=16)))
    assert second.preview_generation == first.preview_generation + 1
    assert second.preview_id != first.preview_id


def test_concurrent_preview_refresh_converges():
    repo = InMemoryAutomationRepository()
    coordinator = AutomationCoordinator(repo)
    coordinator.save_preview(make_preview(now=NOW))
    with ThreadPoolExecutor(max_workers=2) as pool:
        refreshed = list(pool.map(coordinator.save_preview, (make_preview(now=NOW + timedelta(minutes=16)),) * 2))
    assert refreshed[0].preview_id == refreshed[1].preview_id


def executed_for_verification(repo):
    execution = queue(repo, make_preview())
    execution.state = ExecutionState.VERIFICATION_PENDING
    execution.execution_started_at = NOW + timedelta(seconds=10)
    execution.operation_reference = "provider-op"
    execution.attempt = 1
    repo.executions[execution.execution_id] = execution
    return execution


def test_pre_execution_evidence_cannot_verify():
    repo = InMemoryAutomationRepository()
    execution = executed_for_verification(repo)
    result = verify(
        repo, execution, VerificationEvidence(reference="e", target_id="scanner-real", observed_at=NOW, successful=True)
    )
    assert result.state == ExecutionState.VERIFICATION_FAILED
    event = next(value for key, value in repo.events.items() if key.startswith("verification_event:"))
    assert event["metadata"]["verified_execution"] is False


def test_wrong_target_success_flag_is_unverified():
    repo = InMemoryAutomationRepository()
    execution = executed_for_verification(repo)
    result = verify(
        repo,
        execution,
        VerificationEvidence(reference="e", target_id="wrong", observed_at=NOW + timedelta(minutes=1), successful=True),
    )
    assert result.state == ExecutionState.VERIFICATION_FAILED


def test_stale_success_flag_is_unverified():
    test_pre_execution_evidence_cannot_verify()


def test_approval_decision_event_recovers_after_append_failure():
    class FailingRepo(InMemoryAutomationRepository):
        fail = True

        def append_event(self, stream, event_id, document):
            if self.fail and document.get("event_type") == "approval_approved":
                self.fail = False
                raise RuntimeError("injected")
            return super().append_event(stream, event_id, document)

    repo = FailingRepo()
    item = make_preview(action="suppress_notifications", actor="requester")
    coordinator = AutomationCoordinator(repo)
    saved = coordinator.save_preview(item)
    approval = coordinator.request_approval(
        saved, requester="requester", idempotency_key="k", reason="safe", impact="safe", now=NOW
    )
    with pytest.raises(RuntimeError):
        coordinator.decide_approval(
            "tenant-a",
            "production",
            approval.approval_id,
            actor="approver",
            permissions={"workflows:approve"},
            approve=True,
            comment="",
            request_id="decision",
            now=NOW,
        )
    assert repo.approvals[approval.approval_id].decision_event_pending
    retried = coordinator.decide_approval(
        "tenant-a",
        "production",
        approval.approval_id,
        actor="approver",
        permissions={"workflows:approve"},
        approve=True,
        comment="",
        request_id="decision",
        now=NOW,
    )
    assert retried.state == ApprovalState.APPROVED
    assert not retried.decision_event_pending


def test_conflicting_second_approval_decision_fails():
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    approval = approve(repo, item)
    with pytest.raises(Conflict):
        AutomationCoordinator(repo).decide_approval(
            "tenant-a",
            "production",
            approval.approval_id,
            actor="other",
            permissions={"workflows:approve"},
            approve=False,
            comment="",
            request_id="other",
            now=NOW,
        )


def test_preview_actor_must_match_execution_actor():
    with pytest.raises(Conflict, match="actor"):
        AutomationCoordinator(InMemoryAutomationRepository()).queue_execution(
            make_preview(actor="requester"),
            actor="executor",
            idempotency_key="k",
            current_incident_revision="7",
            current_target_revision="scanner-rev-3",
            approval_id=None,
            request_id="r",
            now=NOW,
        )


@pytest.mark.parametrize(
    "text",
    [
        "password=hunter2-fake",
        "Bearer fake-token-value-12345",
        "postgres://user:fake@host/db",
        "-----BEGIN PRIVATE KEY-----",
    ],
)
def test_secret_in_approval_reason_is_rejected(text):
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    with pytest.raises(ValueError, match="credential"):
        AutomationCoordinator(repo).request_approval(
            item, requester="requester", idempotency_key="k", reason=text, impact="safe", now=NOW
        )


def test_secret_in_approval_comment_is_rejected():
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    coordinator = AutomationCoordinator(repo)
    approval = coordinator.request_approval(
        item, requester="requester", idempotency_key="k", reason="safe", impact="safe", now=NOW
    )
    with pytest.raises(ValueError, match="credential"):
        coordinator.decide_approval(
            "tenant-a",
            "production",
            approval.approval_id,
            actor="approver",
            permissions={"workflows:approve"},
            approve=True,
            comment="api_key=fake-key-123456",
            request_id="d",
            now=NOW,
        )


def test_expired_approved_approval_persists_expired_state():
    repo = InMemoryAutomationRepository()
    item = make_preview(action="suppress_notifications", actor="requester")
    approval = approve(repo, item)
    approval.expires_at = NOW + timedelta(seconds=1)
    repo.approvals[approval.approval_id] = approval
    with pytest.raises(Expired):
        AutomationCoordinator(repo).queue_execution(
            item,
            actor=item.actor,
            idempotency_key="late",
            current_incident_revision="7",
            current_target_revision="scanner-rev-3",
            approval_id=approval.approval_id,
            request_id="late",
            now=NOW + timedelta(seconds=2),
        )
    assert repo.approvals[approval.approval_id].state == ApprovalState.EXPIRED
    assert any(event.get("event_type") == "approval_expired" for event in repo.events.values())


def test_rerun_scan_uses_real_scanner_target():
    from services.incident_manager.automation.targets import resolve_target

    target = resolve_target(
        "rerun_scan",
        [{"scanner_id": "scanner-42", "scanner_revision": "9", "asset_id": "asset-a", "source": "finding"}],
    )
    assert target.target_id == "scanner-42"
    assert target.target_revision == "9"
    assert target.target_id != target.affected_asset


def test_ambiguous_scanner_requires_server_resolved_selection():
    from services.incident_manager.automation.targets import TargetSelectionRequired, resolve_target

    evidence = [{"scanner_id": "one", "scanner_revision": "1"}, {"scanner_id": "two", "scanner_revision": "2"}]
    with pytest.raises(TargetSelectionRequired) as error:
        resolve_target("rerun_scan", evidence)
    assert [candidate.target_id for candidate in error.value.candidates] == ["one", "two"]
    assert resolve_target("rerun_scan", evidence, {"target_id": "two", "target_revision": "2"}).target_id == "two"
    with pytest.raises(ValueError, match="authoritative"):
        resolve_target("rerun_scan", evidence, {"target_id": "browser-value", "target_revision": "1"})


def test_execution_state_update_survives_event_append_failure():
    class EventFailRepo(InMemoryAutomationRepository):
        def append_event(self, stream, event_id, document):
            if document.get("event_type") == "execution_verification_pending":
                raise RuntimeError("injected event failure")
            return super().append_event(stream, event_id, document)

    class Accepted:
        action_type = "rerun_scan"
        cancellation_supported = False

        def execute(self, execution):
            return ExecutionResult(True, False, "provider-op")

        def lookup(self, execution):
            return ExecutionResult(True, True, "provider-op")

        def cancel(self, execution):
            return False

    repo = EventFailRepo()
    execution = queue(repo, make_preview())
    assert ExecutionWorker(repo, ExecutorRegistry((Accepted(),)), "worker").run_once(now=NOW) == 1
    stored = repo.executions[execution.execution_id]
    assert stored.state == ExecutionState.VERIFICATION_PENDING
    assert stored.transition_event_pending


def test_verification_update_survives_event_append_failure_without_false_success():
    class EventFailRepo(InMemoryAutomationRepository):
        def append_event(self, stream, event_id, document):
            if stream == "verification_event":
                raise RuntimeError("injected event failure")
            return super().append_event(stream, event_id, document)

    repo = EventFailRepo()
    execution = executed_for_verification(repo)
    saved = verify(
        repo,
        execution,
        VerificationEvidence(
            reference="bad", target_id="wrong", observed_at=NOW + timedelta(minutes=1), successful=True
        ),
    )
    assert saved.state == ExecutionState.VERIFICATION_FAILED
    assert saved.transition_event_pending
