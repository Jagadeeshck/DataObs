from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch

from .filters import isolation_filters

STREAM_ALIASES = {
    "streams": "dataobs-kafka-topics-v1-read",
    "clusters": "dataobs-kafka-clusters-v1-read",
    "consumer_groups": "dataobs-kafka-consumer-groups-v1-read",
    "connectors": "dataobs-kafka-connectors-v1-read",
    "schemas": "dataobs-kafka-schemas-v1-read",
}

SAFE_SOURCE = [
    "@timestamp",
    "observed_at",
    "tenant_id",
    "environment",
    "id",
    "stream_id",
    "cluster_id",
    "connector_id",
    "subject_id",
    "group_id",
    "topic",
    "name",
    "health",
    "reason_codes",
    "partition_count",
    "replication_factor",
    "throughput",
    "lag",
    "lag_velocity",
    "retention_risk",
    "drain_time",
    "state",
    "tasks",
    "compatibility",
    "owner_team",
    "data_products",
    "source_coverage",
]


class StreamRepository:
    def __init__(self, es: Elasticsearch, *, timeout: float = 5.0):
        self.es = es
        self.timeout = timeout

    def search(
        self, resource: str, tenant: str, environment: str, *, size: int = 50, search_after: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        if resource not in STREAM_ALIASES:
            raise ValueError("unsupported stream resource")
        if not 1 <= size <= 200:
            raise ValueError("page size must be between 1 and 200")
        body: dict[str, Any] = {
            "index": STREAM_ALIASES[resource],
            "size": size,
            "query": {"bool": {"filter": isolation_filters(tenant, environment)}},
            "sort": [{"name.keyword": "asc"}, {"id.keyword": "asc"}],
            "source": SAFE_SOURCE,
            "request_timeout": self.timeout,
        }
        if search_after is not None:
            body["search_after"] = search_after
        response = self.es.search(**body)
        return [hit.get("_source", {}) | {"_sort": hit.get("sort", [])} for hit in response["hits"]["hits"]]

    def get(self, resource: str, resource_id: str, tenant: str, environment: str) -> dict[str, Any] | None:
        if resource not in STREAM_ALIASES:
            raise ValueError("unsupported stream resource")
        response = self.es.search(
            index=STREAM_ALIASES[resource],
            size=1,
            source=SAFE_SOURCE,
            query={
                "bool": {"filter": isolation_filters(tenant, environment) + [{"term": {"id.keyword": resource_id}}]}
            },
            request_timeout=self.timeout,
        )
        hits = response["hits"]["hits"]
        return hits[0].get("_source", {}) if hits else None
