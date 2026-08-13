"""Tenant-scoped repository contract and deterministic in-memory implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict
from typing import Any

from .models import DbtProject


class DbtIntelligenceRepository(ABC):
    @abstractmethod
    def upsert_project(self, project: DbtProject) -> None: ...
    @abstractmethod
    def upsert_resource_projection(
        self, tenant: str, environment: str, project: str, resource: dict[str, Any]
    ) -> None: ...
    @abstractmethod
    def append_artifact_event(self, event_id: str, event: dict[str, Any]) -> bool: ...
    @abstractmethod
    def append_project_change(self, change_id: str, change: dict[str, Any]) -> bool: ...
    @abstractmethod
    def list_projects(self, tenant: str, environment: str, limit: int = 100) -> list[dict[str, Any]]: ...
    @abstractmethod
    def list_resources(
        self, tenant: str, environment: str, project: str, resource_type: str | None = None, limit: int = 1000
    ) -> list[dict[str, Any]]: ...
    @abstractmethod
    def list_test_history(
        self, tenant: str, environment: str, test_id: str, limit: int = 100
    ) -> list[dict[str, Any]]: ...
    @abstractmethod
    def runtime_health(self) -> dict[str, Any]: ...


class MemoryDbtIntelligenceRepository(DbtIntelligenceRepository):
    def __init__(self) -> None:
        self.projects: dict[tuple[str, str, str], DbtProject] = {}
        self.resources: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        self.artifact_events: dict[str, dict[str, Any]] = {}
        self.project_changes: dict[str, dict[str, Any]] = {}
        self.test_history: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    def upsert_project(self, project: DbtProject) -> None:
        self.projects[(project.tenant_id, project.environment, project.project_id)] = project

    def upsert_resource_projection(self, tenant: str, environment: str, project: str, resource: dict[str, Any]) -> None:
        self.resources[(tenant, environment, project, resource["resource_id"])] = dict(resource)

    def append_artifact_event(self, event_id: str, event: dict[str, Any]) -> bool:
        if event_id in self.artifact_events:
            return False
        self.artifact_events[event_id] = dict(event)
        return True

    def append_project_change(self, change_id: str, change: dict[str, Any]) -> bool:
        if change_id in self.project_changes:
            return False
        self.project_changes[change_id] = dict(change)
        return True

    def list_projects(self, tenant: str, environment: str, limit: int = 100) -> list[dict[str, Any]]:
        return [asdict(value) for key, value in sorted(self.projects.items()) if key[:2] == (tenant, environment)][
            : max(1, min(limit, 1000))
        ]

    def get_project(self, tenant: str, environment: str, project: str) -> dict[str, Any] | None:
        value = self.projects.get((tenant, environment, project))
        return asdict(value) if value else None

    def list_resources(
        self, tenant: str, environment: str, project: str, resource_type: str | None = None, limit: int = 1000
    ) -> list[dict[str, Any]]:
        values = [
            dict(value)
            for key, value in sorted(self.resources.items())
            if key[:3] == (tenant, environment, project)
            and (resource_type is None or value["resource_type"] == resource_type)
        ]
        return values[: max(1, min(limit, 1000))]

    def list_test_history(self, tenant: str, environment: str, test_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return list(self.test_history[(tenant, environment, test_id)])[-max(1, min(limit, 500)) :]

    def runtime_health(self) -> dict[str, Any]:
        return {"status": "healthy", "backend": "memory", "backlog": 0}
