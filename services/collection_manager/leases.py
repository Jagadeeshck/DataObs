from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .repository import ConflictError, now

TASK_STATES = (
    "available",
    "leased",
    "running",
    "succeeded",
    "failed",
    "retryable",
    "dead_letter",
    "cancelled",
    "expired",
)


def claim_task(repo, tenant_id, scanner_id, task_id, ttl_seconds=60):
    task = repo.get("tasks", task_id, tenant_id)
    if not task or task.get("status") not in {"available", "retryable", "expired"}:
        raise ConflictError(f"task {task_id} is not claimable")
    expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
    return repo.upsert(
        "tasks",
        {**task, "scanner_id": scanner_id, "status": "leased", "lease_owner": scanner_id, "lease_expires_at": expires},
        expected_version=task.get("_version"),
    )


def renew_task(repo, tenant_id, scanner_id, task_id, ttl_seconds=60):
    task = repo.get("tasks", task_id, tenant_id)
    if not task or task.get("lease_owner") != scanner_id:
        raise ConflictError(f"task {task_id} lease is not owned by {scanner_id}")
    return repo.upsert(
        "tasks",
        {
            **task,
            "lease_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(),
            "updated_at": now(),
        },
        expected_version=task.get("_version"),
    )
