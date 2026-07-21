"""Monitor definition lifecycle with revision and ETag concurrency control."""

from __future__ import annotations

from hashlib import sha256
from typing import Protocol

from packages.domain_model.monitor import MonitorDefinition, MonitorState
from services.monitoring.repository import VersionConflict


class DefinitionRepository(Protocol):
    def get_monitor(self, tenant_id: str, environment: str, monitor_id: str) -> MonitorDefinition | None: ...
    def create_monitor(self, monitor: MonitorDefinition) -> MonitorDefinition: ...
    def update_monitor(self, monitor: MonitorDefinition, *, expected_etag: str) -> MonitorDefinition: ...
    def append_definition_event(self, monitor: MonitorDefinition, *, actor: str, action: str) -> None: ...


def definition_etag(monitor: MonitorDefinition) -> str:
    """Return a stable ETag over the semantic definition and revision."""
    payload = monitor.model_dump_json(exclude={"etag", "updated_at"}, by_alias=True)
    return '"' + sha256(payload.encode()).hexdigest() + '"'


_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"enabled", "disabled", "archived"}),
    "recommended": frozenset({"draft", "enabled", "disabled", "archived"}),
    "enabled": frozenset({"learning", "active", "degraded", "disabled", "archived", "error"}),
    "learning": frozenset({"active", "degraded", "suppressed", "disabled", "archived", "error"}),
    "active": frozenset({"degraded", "suppressed", "disabled", "archived", "error"}),
    "degraded": frozenset({"active", "suppressed", "disabled", "archived", "error"}),
    "suppressed": frozenset({"active", "degraded", "disabled", "archived"}),
    "disabled": frozenset({"enabled", "archived"}),
    "error": frozenset({"enabled", "degraded", "disabled", "archived"}),
    "archived": frozenset(),
}


class IllegalTransition(ValueError):
    pass


class DefinitionService:
    def __init__(self, repository: DefinitionRepository) -> None:
        self.repository = repository

    def create(self, monitor: MonitorDefinition, *, actor: str) -> MonitorDefinition:
        monitor.etag = definition_etag(monitor)
        created = self.repository.create_monitor(monitor)
        self.repository.append_definition_event(created, actor=actor, action="created")
        return created

    def update(self, monitor: MonitorDefinition, *, if_match: str | None, actor: str) -> MonitorDefinition:
        if not if_match:
            raise VersionConflict("If-Match is required")
        current = self.repository.get_monitor(monitor.tenant_id, monitor.environment, monitor.id)
        if current is None:
            raise KeyError(monitor.id)
        if current.etag != if_match:
            raise VersionConflict("stale monitor ETag")
        monitor.revision = current.revision + 1
        monitor.etag = definition_etag(monitor)
        saved = self.repository.update_monitor(monitor, expected_etag=if_match)
        self.repository.append_definition_event(saved, actor=actor, action="updated")
        return saved

    def transition(
        self,
        tenant_id: str,
        environment: str,
        monitor_id: str,
        state: MonitorState,
        *,
        if_match: str | None,
        actor: str,
    ) -> MonitorDefinition:
        current = self.repository.get_monitor(tenant_id, environment, monitor_id)
        if current is None:
            raise KeyError(monitor_id)
        target = state.value if isinstance(state, MonitorState) else str(state)
        source = current.state.value if isinstance(current.state, MonitorState) else str(current.state)
        if source == target:
            return current
        if target not in _TRANSITIONS[source]:
            raise IllegalTransition(f"cannot transition monitor from {current.state} to {target}")
        changed = current.model_copy(update={"state": target})
        return self.update(changed, if_match=if_match, actor=actor)
