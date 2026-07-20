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
    "controller_id",
    "broker_count",
    "brokers",
    "offline_partitions",
    "under_replicated_partitions",
    "leaderless_partitions",
    "isr_instability",
    "members",
    "assignments",
    "rebalances",
    "offsets",
    "records_per_second",
    "bytes_per_second",
    "producer_count",
    "consumer_group_count",
    "active_consumer_count",
    "total_lag",
    "maximum_lag",
    "latency_p50",
    "latency_p95",
    "latency_p99",
    "monitor_state",
    "open_incident_count",
    "business_service",
    "schema_state",
    "connector_state",
    "config_fingerprint",
    "dlq",
    "failures",
    "versions",
    "latest_version",
    "fingerprints",
    "references",
    "changes",
    "impact",
]

RESOURCE_ID_FIELDS = {
    "streams": "stream_id",
    "clusters": "cluster_id",
    "consumer_groups": "group_id",
    "connectors": "connector_id",
    "schemas": "subject_id",
}


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
            "sort": [{"name.keyword": "asc"}, {"_id": "asc"}],
            "source": SAFE_SOURCE,
            "request_timeout": self.timeout,
        }
        if search_after is not None:
            body["search_after"] = search_after
        response = self.es.search(**body)
        return [{"document": hit.get("_source", {}), "sort": hit.get("sort", [])} for hit in response["hits"]["hits"]]

    def get(self, resource: str, resource_id: str, tenant: str, environment: str) -> dict[str, Any] | None:
        if resource not in STREAM_ALIASES:
            raise ValueError("unsupported stream resource")
        response = self.es.search(
            index=STREAM_ALIASES[resource],
            size=1,
            source=SAFE_SOURCE,
            query={
                "bool": {
                    "filter": isolation_filters(tenant, environment)
                    + [{"term": {f"{RESOURCE_ID_FIELDS[resource]}.keyword": resource_id}}]
                }
            },
            request_timeout=self.timeout,
        )
        hits = response["hits"]["hits"]
        return hits[0].get("_source", {}) if hits else None

    def history(
        self, resource: str, resource_id: str, tenant: str, environment: str, *, start: str, end: str
    ) -> list[dict[str, Any]]:
        """Return a bounded, safe historical series for measured comparison."""
        if resource not in STREAM_ALIASES:
            raise ValueError("unsupported stream resource")
        response = self.es.search(
            index=STREAM_ALIASES[resource],
            size=500,
            source=SAFE_SOURCE,
            query={
                "bool": {
                    "filter": isolation_filters(tenant, environment)
                    + [
                        {"term": {f"{RESOURCE_ID_FIELDS[resource]}.keyword": resource_id}},
                        {"range": {"@timestamp": {"gte": start, "lte": end}}},
                    ]
                }
            },
            sort=[{"@timestamp": "asc"}],
            request_timeout=self.timeout,
        )
        return [hit.get("_source", {}) for hit in response["hits"]["hits"]]
