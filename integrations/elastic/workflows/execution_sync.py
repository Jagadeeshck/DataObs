from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_STATUS_MAP = {
    "pending": "pending",
    "waiting": "waiting",
    "waiting_for_input": "waiting_for_input",
    "waiting-for-input": "waiting_for_input",
    "running": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
    "timed_out": "timed_out",
    "skipped": "skipped",
}


def normalize_status(value: object) -> str:
    return _STATUS_MAP.get(str(value).lower(), "provider_status_unknown")


def normalize_execution(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": raw.get("workflow_id") or raw.get("workflowId"),
        "workflow_execution_id": raw.get("id") or raw.get("execution_id"),
        "workflow_status": normalize_status(raw.get("status")),
        "started_at": raw.get("started_at") or raw.get("startedAt"),
        "ended_at": raw.get("ended_at") or raw.get("endedAt"),
        "duration_ms": raw.get("duration_ms"),
        "steps": [
            {
                "id": str(step.get("id", ""))[:128],
                "status": normalize_status(step.get("status")),
                "summary": str(step.get("summary", ""))[:500],
            }
            for step in raw.get("steps", [])[:100]
            if isinstance(step, dict)
        ],
        "failure_code": (
            str((raw.get("error") or {}).get("code", ""))[:80]
            if isinstance(raw.get("error"), dict)
            else "provider_failure"
        ),
        "last_synchronized_at": datetime.now(timezone.utc).isoformat(),
    }
