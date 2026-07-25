"""Crash-safe definition operation records (not a cross-index transaction)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

OperationState = Literal["pending", "applied", "superseded", "failed"]


def canonical_checksum(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def operation_id(tenant_id: str, environment: str, monitor_id: str, revision: int, checksum: str) -> str:
    raw = f"v1\0{tenant_id}\0{environment}\0{monitor_id}\0{revision}\0{checksum}"
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class DefinitionOperation:
    operation_id: str
    tenant_id: str
    environment: str
    monitor_id: str
    revision: int
    checksum: str
    actor: str
    reason: str
    action: str
    definition: dict[str, Any]
    state: OperationState = "pending"
    created_at: str = ""

    @classmethod
    def build(cls, definition: Any, *, actor: str, reason: str, action: str) -> "DefinitionOperation":
        payload = definition.model_dump(mode="json") if hasattr(definition, "model_dump") else dict(definition)
        checksum = canonical_checksum(payload)
        return cls(
            operation_id(payload["tenant_id"], payload["environment"], payload["id"], payload["revision"], checksum),
            payload["tenant_id"],
            payload["environment"],
            payload["id"],
            payload["revision"],
            checksum,
            actor,
            reason,
            action,
            payload,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
