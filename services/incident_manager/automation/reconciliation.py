from __future__ import annotations

from datetime import datetime, timezone

from .catalogue import canonical_hash
from .contracts import ApprovalState
from .coordinator import AutomationCoordinator
from .repository import AutomationRepository, Conflict


class AutomationReconciler:
    """Converges durable partial writes without guessing provider outcomes."""

    def __init__(self, repository: AutomationRepository) -> None:
        self.repository = repository
        self.coordinator = AutomationCoordinator(repository)

    def run_once(self, limit: int = 25, now: datetime | None = None) -> int:
        checked = now or datetime.now(timezone.utc)
        repaired = 0
        for execution in self.repository.executions_with_pending_evidence(limit):
            event_id = execution.transition_event_id or canonical_hash(
                [execution.execution_id, execution.state.value, execution.attempt]
            )
            try:
                self.repository.append_event(
                    "remediation_action",
                    event_id,
                    {
                        "@timestamp": execution.updated_at.isoformat(),
                        "tenant_id": execution.tenant_id,
                        "environment": execution.environment,
                        "incident_id": execution.incident_id,
                        "workflow_execution_id": execution.execution_id,
                        "event_type": f"execution_{execution.state.value}",
                        "action_type": execution.action_type,
                        "retry_count": max(execution.attempt - 1, 0),
                        "terminal_state": execution.state.value
                        in {"verified", "verification_failed", "failed", "cancelled", "timed_out"},
                        "request_id": execution.request_id,
                        "correlation_id": execution.action_fingerprint,
                        "metadata": {
                            "attempt": execution.attempt,
                            "error_code": execution.error_code,
                            "catalogue_hash": execution.catalogue_hash,
                            "policy_hash": execution.policy_hash,
                        },
                    },
                )
                execution.transition_event_pending = False
                self.repository.update_execution(execution, execution.lease_token)
                repaired += 1
            except Conflict:
                continue
        for approval in self.repository.approvals_requiring_reconciliation(limit, checked):
            try:
                if approval.decision_event_pending:
                    self.coordinator._deliver_decision_event(approval)
                    repaired += 1
                    continue
                if approval.state == ApprovalState.APPROVED and approval.expires_at <= checked:
                    self.coordinator.expire_approval(
                        approval, actor="automation-reconciler", request_id=approval.request_id, now=checked
                    )
                    repaired += 1
                    continue
                if approval.state != ApprovalState.RESERVED or not approval.reserved_execution_id:
                    continue
                execution = self.repository.get_execution(
                    approval.tenant_id, approval.environment, approval.reserved_execution_id
                )
                if execution:
                    self.coordinator.consume_reservation(approval)
                    repaired += 1
                elif approval.reservation_expires_at and approval.reservation_expires_at <= checked:
                    # Publication always precedes provider submission, so absence of the deterministic
                    # execution projection proves this reservation never reached a provider.
                    old = approval.revision
                    approval.state = ApprovalState.APPROVED
                    approval.reserved_execution_id = None
                    approval.reserved_by = None
                    approval.reserved_at = None
                    approval.reservation_expires_at = None
                    approval.reservation_request_id = None
                    self.repository.update_approval(approval, old)
                    repaired += 1
            except Conflict:
                continue
        return repaired
