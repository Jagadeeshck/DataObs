from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Protocol

from .contracts import CaseLink


class CaseLinkConflict(RuntimeError):
    pass


class CaseLinkRepository(Protocol):
    def get_for_incident(self, tenant_id: str, environment: str, incident_id: str, space: str) -> CaseLink | None: ...
    def reserve(self, link: CaseLink) -> CaseLink: ...
    def update(self, link: CaseLink, expected_revision: int) -> CaseLink: ...


class InMemoryCaseLinkRepository:
    def __init__(self) -> None:
        self._items: dict[str, CaseLink] = {}
        self._lock = Lock()

    def get_for_incident(self, tenant_id: str, environment: str, incident_id: str, space: str) -> CaseLink | None:
        item = self._items.get(f"{tenant_id}:{environment}:{incident_id}:{space}")
        return deepcopy(item)

    def reserve(self, link: CaseLink) -> CaseLink:
        key = f"{link.tenant_id}:{link.environment}:{link.incident_id}:{link.kibana_space}"
        with self._lock:
            existing = self._items.setdefault(key, link.model_copy(deep=True))
            if existing.reconciliation_reference != link.reconciliation_reference:
                raise CaseLinkConflict("case reservation identity conflict")
            return existing.model_copy(deep=True)

    def update(self, link: CaseLink, expected_revision: int) -> CaseLink:
        key = f"{link.tenant_id}:{link.environment}:{link.incident_id}:{link.kibana_space}"
        with self._lock:
            current = self._items.get(key)
            if not current or current.revision != expected_revision:
                raise CaseLinkConflict("case link revision conflict")
            link.revision += 1
            self._items[key] = link.model_copy(deep=True)
            return link.model_copy(deep=True)
