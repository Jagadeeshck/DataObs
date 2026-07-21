from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

MAX_DURATION = timedelta(days=31)


def create_suppression(
    *,
    tenant_id: str,
    environment: str,
    monitor_id: str,
    actor: str,
    reason: str,
    approval_reference: str,
    starts_at: datetime,
    ends_at: datetime,
) -> dict:
    if not actor or not reason or not approval_reference:
        raise ValueError("actor, reason and approval_reference are required")
    if starts_at.tzinfo is None or ends_at.tzinfo is None or ends_at <= starts_at or ends_at - starts_at > MAX_DURATION:
        raise ValueError("suppression duration must be positive, timezone-aware and at most 31 days")
    return {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "environment": environment,
        "monitor_id": monitor_id,
        "actor": actor,
        "reason": reason,
        "approval_reference": approval_reference,
        "starts_at": starts_at.astimezone(timezone.utc).isoformat(),
        "ends_at": ends_at.astimezone(timezone.utc).isoformat(),
        "state": "active",
    }
