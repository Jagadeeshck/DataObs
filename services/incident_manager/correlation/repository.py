from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from .contracts import CorrelationDecision, CorrelationGroup

MAX_CANDIDATES = 50
MAX_MEMBER_SAMPLE = 100
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class StoredGroup:
    group: CorrelationGroup
    seq_no: int
    primary_term: int


@dataclass(frozen=True)
class DeferredEvaluation:
    operation_id: str
    tenant_id: str
    environment: str
    incident_id: str
    incident_revision: str
    phase: str
    created_at: datetime
    attempt: int = 0
    next_attempt_at: datetime | None = None
    completed_at: datetime | None = None


class CorrelationRepository(Protocol):
    def create_group(self, group: CorrelationGroup) -> StoredGroup: ...
    def get_group(self, tenant_id: str, environment: str, group_id: str) -> StoredGroup | None: ...
    def update_group(self, stored: StoredGroup) -> StoredGroup: ...
    def find_candidate_groups(
        self, tenant_id: str, environment: str, incident: Any, *, limit: int = MAX_CANDIDATES
    ) -> list[StoredGroup]: ...
    def find_group_for_incident(self, tenant_id: str, environment: str, incident_id: str) -> StoredGroup | None: ...
    def list_groups(self, tenant_id: str, environment: str, *, limit: int = 25) -> list[StoredGroup]: ...
    def append_decision(self, tenant_id: str, environment: str, decision: CorrelationDecision) -> bool: ...
    def has_decision(self, tenant_id: str, environment: str, decision_id: str) -> bool: ...
    def list_decisions(
        self, tenant_id: str, environment: str, group_id: str, *, limit: int = MAX_PAGE_SIZE
    ) -> list[dict[str, Any]]: ...
    def record_deferred(self, item: DeferredEvaluation) -> bool: ...
    def list_deferred(self, *, limit: int) -> list[DeferredEvaluation]: ...
    def mark_reconciled(self, operation_id: str, completed_at: datetime) -> None: ...


class InMemoryCorrelationRepository:
    """Test repository; production composition uses Elasticsearch."""

    def __init__(self) -> None:
        self.groups: dict[str, StoredGroup] = {}
        self.decisions: dict[str, tuple[str, str, CorrelationDecision]] = {}
        self.deferred: dict[str, DeferredEvaluation] = {}

    def create_group(self, group: CorrelationGroup) -> StoredGroup:
        if group.id in self.groups:
            raise RuntimeError("version conflict")
        stored = StoredGroup(deepcopy(group), 0, 1)
        self.groups[group.id] = stored
        return deepcopy(stored)

    def get_group(self, tenant_id: str, environment: str, group_id: str) -> StoredGroup | None:
        item = self.groups.get(group_id)
        return (
            deepcopy(item)
            if item and (item.group.tenant_id, item.group.environment) == (tenant_id, environment)
            else None
        )

    def update_group(self, stored: StoredGroup) -> StoredGroup:
        current = self.groups.get(stored.group.id)
        if not current or (current.seq_no, current.primary_term) != (stored.seq_no, stored.primary_term):
            raise RuntimeError("version conflict")
        updated = StoredGroup(deepcopy(stored.group), stored.seq_no + 1, stored.primary_term)
        self.groups[stored.group.id] = updated
        return deepcopy(updated)

    def find_candidate_groups(
        self, tenant_id: str, environment: str, incident: Any, *, limit: int = MAX_CANDIDATES
    ) -> list[StoredGroup]:
        assets = set(incident.affected_assets)
        values = [
            v
            for v in self.groups.values()
            if (v.group.tenant_id, v.group.environment) == (tenant_id, environment)
            and assets.intersection(v.group.metadata.get("affected_assets", []))
        ]
        return deepcopy(
            sorted(values, key=lambda v: (-v.group.last_observed_at.timestamp(), v.group.id))[
                : min(limit, MAX_CANDIDATES)
            ]
        )

    def find_group_for_incident(self, tenant_id: str, environment: str, incident_id: str) -> StoredGroup | None:
        for item in self.groups.values():
            if (item.group.tenant_id, item.group.environment) == (
                tenant_id,
                environment,
            ) and incident_id in self.member_ids(item.group.id):
                return deepcopy(item)
        return None

    def list_groups(self, tenant_id: str, environment: str, *, limit: int = 25) -> list[StoredGroup]:
        return deepcopy(
            sorted(
                (
                    v
                    for v in self.groups.values()
                    if (v.group.tenant_id, v.group.environment) == (tenant_id, environment)
                ),
                key=lambda v: (-v.group.last_observed_at.timestamp(), v.group.id),
            )[: min(limit, MAX_PAGE_SIZE)]
        )

    def member_ids(self, group_id: str) -> list[str]:
        return sorted(
            {
                d.incident_id
                for _, _, d in self.decisions.values()
                if d.group_id == group_id and d.action in {"attach", "create"}
            }
        )

    def append_decision(self, tenant_id: str, environment: str, decision: CorrelationDecision) -> bool:
        if decision.decision_id in self.decisions:
            return False
        self.decisions[decision.decision_id] = (tenant_id, environment, deepcopy(decision))
        return True

    def has_decision(self, tenant_id: str, environment: str, decision_id: str) -> bool:
        item = self.decisions.get(decision_id)
        return bool(item and item[:2] == (tenant_id, environment))

    def list_decisions(
        self, tenant_id: str, environment: str, group_id: str, *, limit: int = MAX_PAGE_SIZE
    ) -> list[dict[str, Any]]:
        from .storage import decision_to_api

        items = [
            decision_to_api(v[2])
            for v in self.decisions.values()
            if v[:2] == (tenant_id, environment) and v[2].group_id == group_id
        ]
        return sorted(items, key=lambda v: (v["evaluated_at"], v["decision_id"]))[: min(limit, MAX_PAGE_SIZE)]

    def record_deferred(self, item: DeferredEvaluation) -> bool:
        if item.operation_id in self.deferred:
            return False
        self.deferred[item.operation_id] = deepcopy(item)
        return True

    def list_deferred(self, *, limit: int) -> list[DeferredEvaluation]:
        return deepcopy(
            sorted(
                (v for v in self.deferred.values() if not v.completed_at), key=lambda v: (v.created_at, v.operation_id)
            )[:limit]
        )

    def mark_reconciled(self, operation_id: str, completed_at: datetime) -> None:
        item = self.deferred[operation_id]
        self.deferred[operation_id] = DeferredEvaluation(**{**item.__dict__, "completed_at": completed_at})
