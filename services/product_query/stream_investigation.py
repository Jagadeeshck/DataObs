"""Bounded, allowlisted historical investigation queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SNAPSHOT_ALIAS = "logs-dataobs.pathway-topology-snapshot-*"
MAX_RESULTS = 500


class StreamInvestigationRepository:
    def __init__(self, es: Any):
        self.es = getattr(es, "es", es)

    def topology_as_of(self, tenant: str, environment: str, pathway_id: str, at: datetime) -> dict[str, Any] | None:
        response = self.es.search(
            index=SNAPSHOT_ALIAS,
            size=1,
            source=[
                "snapshot_id",
                "tenant_id",
                "environment",
                "pathway_id",
                "effective_at",
                "observed_at",
                "graph_hash",
                "nodes",
                "edges",
                "node_ids",
                "edge_ids",
                "node_count",
                "edge_count",
                "classification",
                "confidence",
                "source_coverage",
                "missing_inputs",
                "change_reason_codes",
                "evidence_refs",
                "schema_version",
            ],
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {"term": {"pathway_id": pathway_id}},
                        {"range": {"effective_at": {"lte": at.isoformat()}}},
                    ]
                }
            },
            sort=[{"effective_at": "desc"}, {"snapshot_id": "asc"}],
            request_timeout=5,
        )
        hits = response.get("hits", {}).get("hits", [])
        return hits[0]["_source"] if hits else None

    def topology_between(
        self,
        tenant: str,
        environment: str,
        pathway_id: str,
        start: datetime,
        end: datetime,
        *,
        limit: int = 100,
        after: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        self._validate_range(start, end)
        size = min(max(limit, 1), MAX_RESULTS)
        query: dict[str, Any] = {
            "index": SNAPSHOT_ALIAS,
            "size": size,
            "source": [
                "snapshot_id",
                "effective_at",
                "observed_at",
                "graph_hash",
                "node_count",
                "edge_count",
                "classification",
                "change_reason_codes",
                "confidence",
                "source_coverage",
            ],
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {"term": {"pathway_id": pathway_id}},
                        {"range": {"effective_at": {"gte": start.isoformat(), "lte": end.isoformat()}}},
                    ]
                }
            },
            "sort": [{"effective_at": "desc"}, {"snapshot_id": "asc"}],
            "request_timeout": 5,
        }
        if after:
            query["search_after"] = after
        return [
            hit["_source"] | {"_sort": hit.get("sort", [])}
            for hit in self.es.search(**query).get("hits", {}).get("hits", [])
        ]

    def metric_series(
        self, tenant: str, environment: str, resource_id: str, start: datetime, end: datetime, *, limit: int = 500
    ) -> list[dict[str, Any]]:
        return self._history("metrics-dataobs.pathway-*", tenant, environment, resource_id, start, end, limit)

    def reliability_history(
        self, tenant: str, environment: str, resource_id: str, start: datetime, end: datetime, *, limit: int = 200
    ) -> list[dict[str, Any]]:
        return self._history(
            "logs-dataobs.stream-reliability-evaluation-*", tenant, environment, resource_id, start, end, limit
        )

    def anomaly_history(
        self, tenant: str, environment: str, resource_id: str, start: datetime, end: datetime, *, limit: int = 200
    ) -> list[dict[str, Any]]:
        return self._history(
            "metrics-dataobs.stream-anomaly-evaluation-*", tenant, environment, resource_id, start, end, limit
        )

    retention_history = anomaly_history
    change_history = reliability_history
    signal_history = anomaly_history

    def _history(
        self, index: str, tenant: str, environment: str, resource_id: str, start: datetime, end: datetime, limit: int
    ) -> list[dict[str, Any]]:
        self._validate_range(start, end)
        result = self.es.search(
            index=index,
            size=min(max(limit, 1), MAX_RESULTS),
            source=[
                "@timestamp",
                "observed_at",
                "effective_at",
                "resource_id",
                "pathway_id",
                "state",
                "value",
                "confidence",
                "source_coverage",
                "evidence_ref",
                "event_type",
                "severity",
            ],
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {"term": {"resource_id": resource_id}},
                        {"range": {"@timestamp": {"gte": start.isoformat(), "lte": end.isoformat()}}},
                    ]
                }
            },
            sort=[{"@timestamp": "asc"}, {"_id": "asc"}],
            request_timeout=5,
        )
        return [hit["_source"] for hit in result.get("hits", {}).get("hits", [])]

    @staticmethod
    def _validate_range(start: datetime, end: datetime) -> None:
        if end <= start or end - start > timedelta(days=90) or end > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("investigation range must be valid, non-future, and at most 90 days")
