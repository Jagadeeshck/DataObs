from __future__ import annotations

from collections.abc import Callable, Iterable

from packages.domain_model.data_product import DataProductRevisionEvent


class DataProductReconciler:
    """Bounded reconciliation facade. Claiming and fencing remain repository-owned."""

    def __init__(self, repository: object) -> None:
        self.repository = repository

    def reconcile_operation(self, tenant_id: str, environment: str, operation_id: str) -> str:
        event = getattr(self.repository, "get_operation")(tenant_id, environment, operation_id)
        if event is None:
            return "missing"
        current = getattr(self.repository, "get_product")(tenant_id, environment, event.product_id)
        if current and current.revision == event.revision and current.etag == event.etag:
            if event.outcome == "pending":
                getattr(self.repository, "finish_operation")(
                    event.model_copy(update={"outcome": "applied", "applied_at": current.updated_at})
                )
            return "applied"
        if current and current.revision > event.revision:
            getattr(self.repository, "finish_operation")(event.model_copy(update={"outcome": "superseded"}))
            return "superseded"
        return "retry"

    def reconcile_proposal_decision(self, tenant_id: str, environment: str, product_id: str, proposal_id: str) -> str:
        """Inspect immutable evidence and projection without inventing a cross-index transaction."""
        proposal = getattr(self.repository, "get_membership_proposal")(tenant_id, environment, product_id, proposal_id)
        if proposal is None:
            return "missing"
        decisions = getattr(self.repository, "list_membership_decisions")(
            tenant_id, environment, product_id, limit=200
        ).items
        terminal = [event for event in decisions if event.proposal_id == proposal_id and event.outcome == "applied"]
        if terminal and proposal.state != "proposed":
            return "applied"
        if proposal.state != "proposed":
            return "terminal_evidence_missing"
        return "retry"

    def reconcile_membership_exclusion(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> str:
        membership = getattr(self.repository, "get_membership")(tenant_id, environment, product_id, membership_id)
        if membership is None:
            return "missing"
        decisions = getattr(self.repository, "list_membership_decisions")(
            tenant_id, environment, product_id, limit=200
        ).items
        terminal = [
            event
            for event in decisions
            if event.membership_id == membership_id and event.decision == "exclude" and event.outcome == "applied"
        ]
        if membership.state == "excluded" and terminal:
            return "applied"
        if membership.state == "excluded":
            return "terminal_evidence_missing"
        return "retry"

    def run(self, tenant_id: str, environment: str, *, limit: int = 100) -> dict[str, int]:
        events = getattr(self.repository, "list_pending_operations")(tenant_id, environment, limit=limit)
        outcomes = {"applied": 0, "superseded": 0, "retry": 0, "missing": 0}
        for event in events:
            outcome = self.reconcile_operation(tenant_id, environment, event.operation_id)
            outcomes[outcome] += 1
        return outcomes


OperationReconciler = DataProductReconciler


def reconcile_pending(
    events: Iterable[DataProductRevisionEvent], apply: Callable[[DataProductRevisionEvent], None], *, limit: int = 100
) -> int:
    """Apply a deterministic bounded batch; callers persist applied/superseded outcomes."""
    if not 1 <= limit <= 1000:
        raise ValueError("reconciliation limit outside bounds")
    pending = sorted(
        (event for event in events if event.outcome == "pending"), key=lambda e: (e.revision, e.operation_id)
    )
    for event in pending[:limit]:
        apply(event)
    return min(len(pending), limit)
