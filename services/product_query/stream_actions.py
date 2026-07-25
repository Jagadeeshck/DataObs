from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock

ALLOWED_ACTIONS = {
    "restart_failed_connector",
    "restart_failed_task",
    "submit_consumer_scaling",
    "rerun_schema_validation",
    "verify_recovery",
}


@dataclass
class ActionRecord:
    action_id: str
    tenant: str
    environment: str
    target_id: str
    action: str
    reason: str
    requester: str
    state: str
    requested_at: str
    idempotency_key: str


class ActionStore:
    """Lifecycle boundary. Production adapters can persist the same records in the action alias."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ActionRecord] = {}
        self._lock = Lock()

    def request(
        self,
        *,
        tenant: str,
        environment: str,
        target_id: str,
        action: str,
        reason: str,
        requester: str,
        idempotency_key: str,
        eligible: bool,
    ) -> dict[str, str]:
        if action not in ALLOWED_ACTIONS:
            raise ValueError("action is not allowlisted")
        key = (tenant, idempotency_key)
        with self._lock:
            existing = self._records.get(key)
            if existing:
                if (existing.target_id, existing.action) != (target_id, action):
                    raise ValueError("idempotency key was already used for another request")
                return asdict(existing)
            digest = hashlib.sha256(f"{tenant}:{environment}:{idempotency_key}".encode()).hexdigest()[:24]
            record = ActionRecord(
                digest,
                tenant,
                environment,
                target_id,
                action,
                reason,
                requester,
                "awaiting_approval" if eligible else "rejected",
                datetime.now(timezone.utc).isoformat(),
                idempotency_key,
            )
            self._records[key] = record
            return asdict(record)

    def list(self, tenant: str, environment: str, target_id: str) -> list[dict[str, str]]:
        return [
            asdict(item)
            for item in self._records.values()
            if item.tenant == tenant and item.environment == environment and item.target_id == target_id
        ]
