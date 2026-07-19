from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RestartRequest:
    connector: str
    task_id: int
    operator: str
    reason: str
    idempotency_key: str
    approval_id: str


class ApprovedRestartService:
    def __init__(self, client: Any, allowed_targets: set[str]):
        self.client = client
        self.allowed_targets = allowed_targets
        self.results: dict[str, dict[str, Any]] = {}

    def restart(self, request: RestartRequest, *, approved: bool) -> dict[str, Any]:
        if request.idempotency_key in self.results:
            return self.results[request.idempotency_key]
        if not approved or not request.approval_id:
            raise PermissionError("approval required")
        if request.connector not in self.allowed_targets:
            raise PermissionError("connector is not allowlisted")
        before = self.client.status(request.connector)
        tasks = {int(task["id"]): task for task in before.get("tasks", [])}
        if tasks.get(request.task_id, {}).get("state") != "FAILED":
            raise ValueError("only failed tasks can be restarted")
        self.client.restart_failed_task(request.connector, request.task_id, approved=True)
        after = self.client.status(request.connector)
        result = {
            "action": "restart_failed_task",
            "target": f"{request.connector}:{request.task_id}",
            "operator": request.operator,
            "reason": request.reason,
            "approval_id": request.approval_id,
            "idempotency_key": request.idempotency_key,
            "recovery_verified": any(
                int(task["id"]) == request.task_id and task.get("state") == "RUNNING" for task in after.get("tasks", [])
            ),
        }
        self.results[request.idempotency_key] = result
        return result
