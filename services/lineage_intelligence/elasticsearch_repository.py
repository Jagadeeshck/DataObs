from __future__ import annotations

from dataclasses import fields
from typing import Any

from elasticsearch import Elasticsearch

from .models import LineageEdge

DATASET_EDGES = "dataobs-lineage-current-v1-read"
COLUMN_EDGES = "dataobs-column-lineage-current-v1-read"


class ElasticsearchLineageRepository:
    """Bounded ES 9.x repository using scoped, frontier-based adjacency queries."""

    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    @staticmethod
    def _scope(tenant_id: str, environment: str) -> list[dict[str, Any]]:
        return [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]

    @staticmethod
    def _edge(source: dict[str, Any]) -> LineageEdge:
        allowed = {item.name for item in fields(LineageEdge)}
        values = {key: value for key, value in source.items() if key in allowed}
        values["evidence_refs"] = tuple(values.get("evidence_refs", ()))
        return LineageEdge(**values)

    def get_asset_node(self, tenant_id: str, environment: str, asset_id: str) -> dict | None:
        result = self.client.search(
            index="dataobs-assets-v1-read",
            size=1,
            query={"bool": {"filter": [*self._scope(tenant_id, environment), {"term": {"asset_id": asset_id}}]}},
        )
        hits = result["hits"]["hits"]
        return dict(hits[0]["_source"]) if hits else None

    def get_edge(self, tenant_id: str, environment: str, edge_id: str) -> LineageEdge | None:
        for index in (DATASET_EDGES, COLUMN_EDGES):
            result = self.client.search(
                index=index,
                size=1,
                query={"bool": {"filter": [*self._scope(tenant_id, environment), {"term": {"edge_id": edge_id}}]}},
            )
            if result["hits"]["hits"]:
                return self._edge(result["hits"]["hits"][0]["_source"])
        return None

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
        if not node_ids or len(node_ids) > 1000 or not 1 <= limit <= 2500:
            raise ValueError("adjacency query exceeds a safety bound")
        should = []
        if direction in {"downstream", "both"}:
            should.append({"terms": {"source_asset_id": list(node_ids)}})
        if direction in {"upstream", "both"}:
            should.append({"terms": {"target_asset_id": list(node_ids)}})
        filters: list[dict[str, Any]] = [
            *self._scope(tenant_id, environment),
            {"term": {"active": True}},
            {"bool": {"should": should, "minimum_should_match": 1}},
        ]
        if not include_stale:
            filters.append({"term": {"stale": False}})
        if as_of:
            filters.append({"range": {"observed_at": {"lte": as_of}}})
        result = self.client.search(
            index=COLUMN_EDGES if column else DATASET_EDGES,
            size=limit,
            timeout="5s",
            query={"bool": {"filter": filters}},
            sort=["source_asset_id", "target_asset_id", "edge_id"],
        )
        return [self._edge(hit["_source"]) for hit in result["hits"]["hits"]]

    def _edges_by(self, tenant_id: str, environment: str, field: str, value: str, limit: int) -> list[LineageEdge]:
        result = self.client.search(
            index=DATASET_EDGES,
            size=min(limit, 500),
            query={"bool": {"filter": [*self._scope(tenant_id, environment), {"term": {field: value}}]}},
            sort=["edge_id"],
        )
        return [self._edge(hit["_source"]) for hit in result["hits"]["hits"]]

    def list_edges_by_job(self, tenant_id: str, environment: str, job_id: str, limit: int = 500) -> list[LineageEdge]:
        return self._edges_by(tenant_id, environment, "job_id", job_id, limit)

    def list_edges_by_run(self, tenant_id: str, environment: str, run_id: str, limit: int = 500) -> list[LineageEdge]:
        return self._edges_by(tenant_id, environment, "run_id", run_id, limit)

    def append_schema_change(self, tenant_id: str, environment: str, change: dict) -> None:
        doc = {**change, "tenant_id": tenant_id, "environment": environment}
        self.client.create(index="logs-dataobs.lineage-change-default", id=change["change_id"], document=doc)

    def list_schema_changes(self, tenant_id: str, environment: str, limit: int = 100) -> list[dict]:
        result = self.client.search(
            index="logs-dataobs.lineage-change-*",
            size=min(limit, 100),
            query={"bool": {"filter": self._scope(tenant_id, environment)}},
            sort=[{"observed_at": "desc"}, {"change_id": "asc"}],
        )
        return [dict(hit["_source"]) for hit in result["hits"]["hits"]]

    def append_impact_evaluation(self, tenant_id: str, environment: str, evaluation: dict) -> None:
        self.client.create(
            index="logs-dataobs.lineage-impact-evaluation-default",
            id=evaluation["analysis_id"],
            document={**evaluation, "tenant_id": tenant_id, "environment": environment},
        )

    def get_impact_evaluation(self, tenant_id: str, environment: str, analysis_id: str) -> dict | None:
        result = self.client.search(
            index="logs-dataobs.lineage-impact-evaluation-*",
            size=1,
            query={"bool": {"filter": [*self._scope(tenant_id, environment), {"term": {"analysis_id": analysis_id}}]}},
        )
        hits = result["hits"]["hits"]
        return dict(hits[0]["_source"]) if hits else None
