"""Persistence-only SLO records; evaluation semantics live in domain_model.slo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DefinitionRevision:
    slo_id: str
    revision: int
    actor: str
    reason: str
    recorded_at: datetime
    definition: dict[str, Any]


@dataclass(frozen=True)
class RuntimeState:
    tenant_id: str
    environment: str
    slo_id: str
    next_evaluation_at: datetime
    fencing_token: int = 0
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    last_checkpoint: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    attempt_count: int = 0
