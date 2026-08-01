from __future__ import annotations

from typing import Any, Literal

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
    "partitions",
    "metrics",
    "configuration",
    "pathways",
    "incidents",
    "consumer_groups",
    "cleanup_policy",
    "retention_ms",
    "min_insync_replicas",
    "producer_rate",
    "consumer_rate",
    "protocol",
    "coordinator",
    "member_count",
    "assigned_partition_count",
    "lag_heatmap",
    "retention_risk_detail",
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
        self,
        resource: str,
        tenant: str,
        environment: str,
        *,
        size: int = 50,
        search_after: list[Any] | None = None,
        search: str | None = None,
        health: str | None = None,
        retention_risk: str | None = None,
        cluster_id: str | None = None,
        consumer_group_id: str | None = None,
        has_lag: bool | None = None,
        sort: Literal["topic", "last_observed", "maximum_lag", "throughput", "retention_risk", "health"] = "topic",
    ) -> list[dict[str, Any]]:
        if resource not in STREAM_ALIASES:
            raise ValueError("unsupported stream resource")
        if not 1 <= size <= 200:
            raise ValueError("page size must be between 1 and 200")
        filters = isolation_filters(tenant, environment)
        for field, value in (
            ("health.keyword", health),
            ("retention_risk.keyword", retention_risk),
            ("cluster_id.keyword", cluster_id),
            ("consumer_groups.group_id.keyword", consumer_group_id),
        ):
            if value:
                filters.append({"term": {field: value}})
        query: dict[str, Any] = {"bool": {"filter": filters}}
        if search:
            # User text is data in a match query, never executable wildcard syntax.
            query["bool"]["must"] = [{"multi_match": {"query": search, "fields": ["topic", "name"]}}]
        if has_lag is True:
            filters.append({"range": {"maximum_lag": {"gt": 0}}})
        elif has_lag is False:
            filters.append({"range": {"maximum_lag": {"lte": 0}}})
        sort_fields: dict[str, tuple[str, str]] = {
            "topic": ("topic.keyword", "asc"),
            "last_observed": ("observed_at", "desc"),
            "maximum_lag": ("maximum_lag", "desc"),
            "throughput": ("records_per_second", "desc"),
            "retention_risk": ("retention_risk.keyword", "asc"),
            "health": ("health.keyword", "asc"),
        }
        field, direction = sort_fields[sort]
        if resource != "streams" and sort == "topic":
            field = "name.keyword"
        body: dict[str, Any] = {
            "index": STREAM_ALIASES[resource],
            "size": size,
            "query": query,
            "sort": [{field: {"order": direction, "missing": "_last"}}, {"_id": "asc"}],
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
