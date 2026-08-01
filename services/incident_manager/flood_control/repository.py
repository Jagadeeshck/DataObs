from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .contracts import FloodDecision, FloodWindow

MAX_STORM_PAGE = 100


@dataclass(frozen=True)
class NotificationDecision:
    decision_id: str
    flood_id: str
    group_id: str
    representative_incident_id: str
    action: str
    reason_codes: tuple[str, ...]
    policy_version: str
    created_at: datetime
    eligibility_at: datetime
    idempotency_key: str
    status: str = "eligible"


@dataclass(frozen=True)
class StoredFlood:
    window: FloodWindow
    projection: dict[str, Any]
    seq_no: int
    primary_term: int


class FloodRepository(Protocol):
    def get_window(self, tenant_id: str, environment: str, flood_id: str) -> StoredFlood | None: ...
    def create_window(self, stored: StoredFlood) -> StoredFlood: ...
    def update_window(self, stored: StoredFlood) -> StoredFlood: ...
    def append_transition(
        self, tenant_id: str, environment: str, event_id: str, flood_id: str, decision: FloodDecision
    ) -> bool: ...
    def append_notification(self, tenant_id: str, environment: str, decision: NotificationDecision) -> bool: ...
    def list_storms(self, tenant_id: str, environment: str, *, limit: int = 25) -> list[StoredFlood]: ...
    def list_timeline(
        self, tenant_id: str, environment: str, flood_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]: ...


class InMemoryFloodRepository:
    def __init__(self) -> None:
        self.windows: dict[str, StoredFlood] = {}
        self.transitions: dict[str, dict[str, Any]] = {}
        self.notifications: dict[str, tuple[str, str, NotificationDecision]] = {}

    def get_window(self, tenant_id: str, environment: str, flood_id: str) -> StoredFlood | None:
        item = self.windows.get(flood_id)
        return (
            deepcopy(item)
            if item and (item.window.tenant_id, item.window.environment) == (tenant_id, environment)
            else None
        )

    def create_window(self, stored: StoredFlood) -> StoredFlood:
        if stored.window.flood_id in self.windows:
            raise RuntimeError("version conflict")
        result = StoredFlood(deepcopy(stored.window), deepcopy(stored.projection), 0, 1)
        self.windows[stored.window.flood_id] = result
        return deepcopy(result)

    def update_window(self, stored: StoredFlood) -> StoredFlood:
        current = self.windows.get(stored.window.flood_id)
        if not current or (current.seq_no, current.primary_term) != (stored.seq_no, stored.primary_term):
            raise RuntimeError("version conflict")
        result = StoredFlood(
            deepcopy(stored.window), deepcopy(stored.projection), stored.seq_no + 1, stored.primary_term
        )
        self.windows[stored.window.flood_id] = result
        return deepcopy(result)

    def append_transition(
        self, tenant_id: str, environment: str, event_id: str, flood_id: str, decision: FloodDecision
    ) -> bool:
        if event_id in self.transitions:
            return False
        self.transitions[event_id] = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "environment": environment,
            "flood_id": flood_id,
            "prior_state": decision.prior_state,
            "new_state": decision.new_state,
            "notification_decision": decision.notification_decision,
            "reason_codes": list(decision.reason_codes),
            "timestamp": decision.window_end.isoformat(),
        }
        return True

    def append_notification(self, tenant_id: str, environment: str, decision: NotificationDecision) -> bool:
        if decision.decision_id in self.notifications:
            return False
        self.notifications[decision.decision_id] = (tenant_id, environment, decision)
        return True

    def list_storms(self, tenant_id: str, environment: str, *, limit: int = 25) -> list[StoredFlood]:
        return deepcopy(
            sorted(
                (
                    v
                    for v in self.windows.values()
                    if (v.window.tenant_id, v.window.environment) == (tenant_id, environment)
                ),
                key=lambda v: (-(v.projection.get("last_observed_at") or datetime.min).timestamp(), v.window.flood_id),
            )[: min(limit, MAX_STORM_PAGE)]
        )

    def list_timeline(
        self, tenant_id: str, environment: str, flood_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        return deepcopy(
            sorted(
                (
                    v
                    for v in self.transitions.values()
                    if (v["tenant_id"], v["environment"], v["flood_id"]) == (tenant_id, environment, flood_id)
                ),
                key=lambda v: (v["timestamp"], v["event_id"]),
            )[: min(limit, MAX_STORM_PAGE)]
        )
