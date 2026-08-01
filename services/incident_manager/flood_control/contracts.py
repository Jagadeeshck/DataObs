from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FloodState(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    FLOODING = "flooding"
    RECOVERING = "recovering"
    CLOSED = "closed"


@dataclass(frozen=True)
class FloodEvent:
    event_id: str
    occurred_at: datetime
    incident_id: str
    asset_id: str | None = None
    source: str | None = None
    severity: str = "medium"
    data_loss_risk: bool = False
    business_services: tuple[str, ...] = ()


@dataclass
class FloodWindow:
    flood_id: str
    tenant_id: str
    environment: str
    group_id: str
    state: FloodState = FloodState.NORMAL
    events: dict[str, FloodEvent] = field(default_factory=dict)
    suppressed_notification_count: int = 0
    last_transition_at: datetime | None = None


@dataclass(frozen=True)
class FloodDecision:
    prior_state: FloodState
    new_state: FloodState
    notification_decision: str
    reason_codes: tuple[str, ...]
    observed: dict[str, float | int]
    thresholds: dict[str, float | int]
    window_start: datetime
    window_end: datetime
    policy_version: str
    evidence_references: tuple[str, ...]
