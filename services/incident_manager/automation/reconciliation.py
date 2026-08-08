from __future__ import annotations

from datetime import datetime, timezone

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
