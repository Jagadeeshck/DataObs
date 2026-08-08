from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

from .models import LineageEdge, SchemaVersion


class LineageRepository(Protocol):
    """Tenant scope is mandatory at the persistence boundary."""

    def get_asset_node(self, tenant_id: str, environment: str, asset_id: str) -> dict | None: ...
    def get_edge(self, tenant_id: str, environment: str, edge_id: str) -> LineageEdge | None: ...
    def list_adjacent_edges(
        self,
        tenant_id: str,
        environment: str,
        node_ids: tuple[str, ...],
        direction: str,
        *,
        column: bool = False,
        include_stale: bool = False,
        as_of: str | None = None,
        limit: int = 500,
    ) -> list[LineageEdge]: ...
    def list_edges_by_job(
        self, tenant_id: str, environment: str, job_id: str, limit: int = 500
    ) -> list[LineageEdge]: ...
    def list_edges_by_run(
        self, tenant_id: str, environment: str, run_id: str, limit: int = 500
    ) -> list[LineageEdge]: ...
    def append_schema_change(self, tenant_id: str, environment: str, change: dict) -> None: ...
    def list_schema_changes(self, tenant_id: str, environment: str, limit: int = 100) -> list[dict]: ...
    def append_impact_evaluation(self, tenant_id: str, environment: str, evaluation: dict) -> None: ...
    def get_impact_evaluation(self, tenant_id: str, environment: str, analysis_id: str) -> dict | None: ...


class MemoryLineageRepository:
    """Deterministic test repository; production wiring must use Elasticsearch."""

    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str, str], dict] = {}
        self.edges: dict[tuple[str, str, str], LineageEdge] = {}
        self.schemas: dict[tuple[str, str, str], list[SchemaVersion]] = {}
        self.changes: dict[tuple[str, str, str], dict] = {}
        self.impacts: dict[tuple[str, str, str], dict] = {}

    def add_edge(self, tenant_id: str, environment: str, edge: LineageEdge) -> None:
        self.edges[(tenant_id, environment, edge.edge_id)] = edge

    def get_asset_node(self, tenant_id: str, environment: str, asset_id: str) -> dict | None:
        value = self.nodes.get((tenant_id, environment, asset_id))
        return dict(value) if value else None

    def get_edge(self, tenant_id: str, environment: str, edge_id: str) -> LineageEdge | None:
        return self.edges.get((tenant_id, environment, edge_id))

    def list_adjacent_edges(
        self,
        tenant_id: str,
        environment: str,
        node_ids: tuple[str, ...],
        direction: str,
        *,
        column: bool = False,
        include_stale: bool = False,
        as_of: str | None = None,
        limit: int = 500,
    ) -> list[LineageEdge]:
        ids = set(node_ids)
        output = []
        for (tenant, env, _), edge in self.edges.items():
            if tenant != tenant_id or env != environment or edge.level != ("column" if column else "dataset"):
                continue
            if not edge.active or (edge.stale and not include_stale) or (as_of and edge.observed_at > as_of):
                continue
            if (direction in {"downstream", "both"} and edge.source_asset_id in ids) or (
                direction in {"upstream", "both"} and edge.target_asset_id in ids
            ):
                output.append(edge)
        return sorted(output, key=lambda e: (e.source_asset_id, e.target_asset_id, e.edge_id))[:limit]

    def _by(self, tenant_id: str, environment: str, field: str, value: str, limit: int) -> list[LineageEdge]:
        return sorted(
            [
                e
                for (t, v, _), e in self.edges.items()
                if t == tenant_id and v == environment and getattr(e, field) == value
            ],
            key=lambda e: e.edge_id,
        )[:limit]

    def list_edges_by_job(self, tenant_id: str, environment: str, job_id: str, limit: int = 500) -> list[LineageEdge]:
        return self._by(tenant_id, environment, "job_id", job_id, limit)

    def list_edges_by_run(self, tenant_id: str, environment: str, run_id: str, limit: int = 500) -> list[LineageEdge]:
        return self._by(tenant_id, environment, "run_id", run_id, limit)

    def append_schema_change(self, tenant_id: str, environment: str, change: dict) -> None:
        self.changes.setdefault((tenant_id, environment, change["change_id"]), dict(change))

    def list_schema_changes(self, tenant_id: str, environment: str, limit: int = 100) -> list[dict]:
        values = [dict(v) for (t, e, _), v in self.changes.items() if t == tenant_id and e == environment]
        return sorted(values, key=lambda x: (x.get("observed_at", ""), x["change_id"]), reverse=True)[:limit]

    def append_impact_evaluation(self, tenant_id: str, environment: str, evaluation: dict) -> None:
        self.impacts.setdefault((tenant_id, environment, evaluation["analysis_id"]), dict(evaluation))

    def get_impact_evaluation(self, tenant_id: str, environment: str, analysis_id: str) -> dict | None:
        value = self.impacts.get((tenant_id, environment, analysis_id))
        return dict(value) if value else None
