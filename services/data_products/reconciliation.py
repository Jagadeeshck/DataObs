from __future__ import annotations

from collections.abc import Callable, Iterable

from packages.domain_model.data_product import DataProductRevisionEvent


class OperationReconciler:
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

    def run(self, tenant_id: str, environment: str, *, limit: int = 100) -> dict[str, int]:
        events = getattr(self.repository, "list_pending_operations")(tenant_id, environment, limit=limit)
        outcomes = {"applied": 0, "superseded": 0, "retry": 0, "missing": 0}
        for event in events:
            outcome = self.reconcile_operation(tenant_id, environment, event.operation_id)
            outcomes[outcome] += 1
        return outcomes


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
