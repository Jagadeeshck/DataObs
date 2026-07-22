from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import timedelta

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductRevisionEvent
from services.data_products.operation_state import DataProductOperationFinalResult, OperationClaimConflict
from services.data_products.repository import DataProductRepository


class DataProductOperationService:
    """Independently runnable, CAS-fenced operation reconciliation service."""

    def __init__(self, repository: DataProductRepository, *, worker_id: str, claim_ttl_seconds: int = 30) -> None:
        self.repository = repository
        self.worker_id = worker_id
        self.claim_ttl_seconds = claim_ttl_seconds

    def get_operation_status(self, tenant_id: str, environment: str, operation_id: str):
        return self.repository.get_operation_state(tenant_id, environment, operation_id)

    def reconcile_operation(self, tenant_id: str, environment: str, operation_id: str) -> str:
        state = self.repository.get_operation_state(tenant_id, environment, operation_id)
        if state is None:
            return "missing"
        if state.status in {"applied", "superseded", "failed"}:
            return state.status
        now = utc_now()
        try:
            claim = self.repository.claim_operation(
                tenant_id,
                environment,
                operation_id,
                worker_id=self.worker_id,
                now=now,
                expires_at=now + timedelta(seconds=self.claim_ttl_seconds),
                expected_seq_no=state.seq_no,
                expected_primary_term=state.primary_term,
            )
        except OperationClaimConflict:
            return "retry"
        # Handlers persist their target result before exposing its immutable reference.
        # A result reference means projections/evidence are complete and only state repair remains.
        claimed = self.repository.get_operation_state(tenant_id, environment, operation_id)
        if claimed and claimed.result_reference:
            self.repository.complete_operation(
                claim, DataProductOperationFinalResult(0, "recovered", claimed.result_reference, now)
            )
            return "applied"
        return "retry"

    def reconcile_batch(self, tenant_id: str, environment: str, *, limit: int = 100) -> dict[str, int]:
        if not 1 <= limit <= 1000:
            raise ValueError("reconciliation limit outside bounds")
        outcomes = {"applied": 0, "superseded": 0, "failed": 0, "retry": 0, "missing": 0}
        for state in self.repository.list_reconcilable_operations(tenant_id, environment, limit=limit):
            outcome = self.reconcile_operation(tenant_id, environment, state.operation_id)
            outcomes[outcome] += 1
        return outcomes


class DataProductReconciler:
    """Bounded reconciliation facade. Claiming and fencing remain repository-owned."""

    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def reconcile_operation(self, tenant_id: str, environment: str, operation_id: str) -> str:
        event = self.repository.get_operation(tenant_id, environment, operation_id)
        if event is None:
            return "missing"
        current = self.repository.get_product(tenant_id, environment, event.product_id)
        if current and current.revision == event.revision and current.etag == event.etag:
            if event.outcome == "pending":
                self.repository.finish_operation(
                    event.model_copy(update={"outcome": "applied", "applied_at": current.updated_at})
                )
            return "applied"
        if current and current.revision > event.revision:
            self.repository.finish_operation(event.model_copy(update={"outcome": "superseded"}))
            return "superseded"
        return "retry"

    def reconcile_proposal_decision(self, tenant_id: str, environment: str, product_id: str, proposal_id: str) -> str:
        """Inspect immutable evidence and projection without inventing a cross-index transaction."""
        proposal = self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)
        if proposal is None:
            return "missing"
        decisions = self.repository.list_membership_decisions(tenant_id, environment, product_id, limit=200).items
        terminal = [event for event in decisions if event.proposal_id == proposal_id and event.outcome == "applied"]
        if terminal and proposal.state != "proposed":
            return "applied"
        if proposal.state != "proposed":
            return "terminal_evidence_missing"
        return "retry"

    def reconcile_membership_exclusion(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> str:
        membership = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
        if membership is None:
            return "missing"
        decisions = self.repository.list_membership_decisions(tenant_id, environment, product_id, limit=200).items
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
        events = self.repository.list_pending_operations(tenant_id, environment, limit=limit)
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
