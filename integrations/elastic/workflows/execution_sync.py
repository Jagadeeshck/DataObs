from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_execution(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": raw.get("workflow_id") or raw.get("workflowId"),
        "workflow_execution_id": raw.get("id") or raw.get("execution_id"),
        "workflow_status": raw.get("status", "running"),
        "started_at": raw.get("started_at") or raw.get("startedAt"),
        "ended_at": raw.get("ended_at") or raw.get("endedAt"),
        "duration_ms": raw.get("duration_ms"),
        "steps": raw.get("steps", []),
        "failure_details": raw.get("error", {}),
        "last_synchronized_at": datetime.now(timezone.utc).isoformat(),
    }
