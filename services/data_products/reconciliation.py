from __future__ import annotations

from collections.abc import Callable, Iterable

from packages.domain_model.data_product import DataProductRevisionEvent


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
