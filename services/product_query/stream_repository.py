from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from elasticsearch import Elasticsearch

from .filters import isolation_filters

STREAM_ALIASES = {
    "streams": "dataobs-kafka-topics-v1-read",
    "clusters": "dataobs-kafka-clusters-v1-read",
    "consumer_groups": "dataobs-kafka-consumer-groups-v1-read",
    "connectors": "dataobs-kafka-connectors-v1-read",
    "schemas": "dataobs-kafka-schemas-v1-read",
    "brokers": "dataobs-kafka-brokers-v1-read",
    "partitions": "dataobs-kafka-partitions-v1-read",
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
    "broker_id",
    "host",
    "port",
    "rack",
    "controller",
    "topic_count",
    "topic_id",
    "partition_id",
    "leader_id",
    "leader_available",
    "under_replicated",
    "offline_replicas",
    "task_count",
    "failed_task_count",
    "worker_count",
    "connector_type",
    "classification",
    "data_status",
]
BROKER_SAFE_SOURCE = [
    "broker_id",
    "cluster_id",
    "host",
    "port",
    "rack",
    "controller",
    "health",
    "reason_codes",
    "observed_at",
    "source_coverage",
    "data_status",
]
RELATED_SAFE_SOURCE = {
    "brokers": BROKER_SAFE_SOURCE,
    "streams": [field for field in SAFE_SOURCE if field not in {"configuration", "config_fingerprint"}],
    "consumer_groups": [field for field in SAFE_SOURCE if field not in {"configuration", "config_fingerprint"}],
    "connectors": [
        "connector_id",
        "cluster_id",
        "name",
        "connector_type",
        "classification",
        "state",
        "task_count",
        "failed_task_count",
        "worker_count",
        "health",
        "reason_codes",
        "observed_at",
        "source_coverage",
        "data_status",
    ],
    "partitions": [
        "cluster_id",
        "topic_id",
        "partition_id",
        "leader_id",
        "leader_available",
        "under_replicated",
        "offline_replicas",
        "health",
        "observed_at",
        "source_coverage",
    ],
}
CLUSTER_SAFE_SOURCE = [
    "cluster_id",
    "name",
    "health",
    "reason_codes",
    "controller_id",
    "broker_count",
    "topic_count",
    "partition_count",
    "consumer_group_count",
    "connector_count",
    "observed_at",
    "source_coverage",
    "data_status",
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
            source=CLUSTER_SAFE_SOURCE if resource == "clusters" else SAFE_SOURCE,
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

    def related(
        self,
        resource: Literal["brokers", "streams", "consumer_groups", "connectors", "partitions"],
        cluster_id: str,
        tenant: str,
        environment: str,
        *,
        size: int = 50,
        search_after: list[Any] | None = None,
        search: str | None = None,
        health: str | None = None,
        retention_risk: str | None = None,
        has_lag: bool | None = None,
        sort: str = "name",
    ) -> list[dict[str, Any]]:
        """Read a bounded cluster projection without trusting caller-supplied indices."""
        if resource not in {"brokers", "streams", "consumer_groups", "connectors", "partitions"}:
            raise ValueError("unsupported cluster resource")
        if not 1 <= size <= 201:
            raise ValueError("page size must be between 1 and 201")
        filters = isolation_filters(tenant, environment) + [{"term": {"cluster_id.keyword": cluster_id}}]
        if health:
            filters.append({"term": {"health.keyword": health}})
        if retention_risk:
            filters.append({"term": {"retention_risk.keyword": retention_risk}})
        if has_lag is True:
            filters.append({"range": {"maximum_lag": {"gt": 0}}})
        elif has_lag is False:
            filters.append({"range": {"maximum_lag": {"lte": 0}}})
        query: dict[str, Any] = {"bool": {"filter": filters}}
        if search:
            query["bool"]["must"] = [{"multi_match": {"query": search, "fields": ["topic", "name"]}}]
        id_fields = {
            "brokers": "broker_id.keyword",
            "streams": "topic.keyword",
            "consumer_groups": "group_id.keyword",
            "connectors": "connector_id.keyword",
            "partitions": "partition_id.keyword",
        }
        sortable = {
            "name": id_fields[resource],
            "topic": "topic.keyword" if resource == "streams" else id_fields[resource],
            "last_observed": "observed_at",
            "maximum_lag": "maximum_lag",
            "health": "health.keyword",
            "retention_risk": "retention_risk.keyword",
        }
        field = sortable.get(sort, id_fields[resource])
        direction = "desc" if sort in {"last_observed", "maximum_lag"} else "asc"
        request: dict[str, Any] = {
            "index": STREAM_ALIASES[resource],
            "size": size,
            "source": RELATED_SAFE_SOURCE[resource],
            "query": query,
            "sort": [{field: {"order": direction, "missing": "_last"}}, {"_id": "asc"}],
            "request_timeout": self.timeout,
        }
        if search_after is not None:
            request["search_after"] = search_after
        response = self.es.search(**request)
        return [{"document": hit.get("_source", {}), "sort": hit.get("sort", [])} for hit in response["hits"]["hits"]]

    def cluster_health(self, cluster: dict[str, Any], tenant: str, environment: str) -> dict[str, Any]:
        """Summarise only observed projections; absent partition evidence stays unknown."""
        cluster_id = str(cluster["cluster_id"])
        resources = {
            name: [hit["document"] for hit in self.related(name, cluster_id, tenant, environment, size=200)]
            for name in ("brokers", "streams", "consumer_groups", "connectors", "partitions")
        }
        brokers, topics, groups, connectors, partitions = (resources[name] for name in resources)
        missing = [name for name, values in resources.items() if not values]
        under_replicated = sum(item.get("under_replicated") is True for item in partitions) if partitions else None
        leaderless = sum(item.get("leader_available") is False for item in partitions) if partitions else None
        offline = sum(len(item.get("offline_replicas") or []) for item in partitions) if partitions else None
        failed_connectors = (
            sum((item.get("state") == "failed") or bool(item.get("failed_task_count")) for item in connectors)
            if connectors
            else None
        )
        healthy_brokers = sum(item.get("health") == "healthy" for item in brokers) if brokers else None
        unhealthy_brokers = (
            sum(item.get("health") in {"warning", "degraded", "critical", "unhealthy"} for item in brokers)
            if brokers
            else None
        )
        reasons: list[str] = []
        health = "healthy"
        if leaderless and leaderless > 0:
            health, reasons = "critical", ["leaderless_partitions"]
        if (offline and offline > 0) or (failed_connectors and failed_connectors > 0):
            if health != "critical":
                health = "critical"
            reasons.extend(
                code
                for code, value in (("offline_replicas", offline), ("failed_connectors", failed_connectors))
                if value
            )
        if under_replicated and under_replicated > 0 and health == "healthy":
            health = "degraded"
            reasons.append("under_replicated_partitions")
        if brokers and not any(item.get("controller") is True for item in brokers) and health == "healthy":
            health = "degraded"
            reasons.append("controller_not_observed")
        now, stale = datetime.now(timezone.utc), 0
        observed_values: list[str] = []
        for values in resources.values():
            for item in values:
                if item.get("observed_at"):
                    observed_values.append(item["observed_at"])
                    try:
                        if now - datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00")) > timedelta(
                            minutes=5
                        ):
                            stale += 1
                    except ValueError:
                        stale += 1
        if not partitions:
            health = "unknown" if health == "healthy" else health
            reasons.append("partition_evidence_missing")
        if stale:
            reasons.append("stale_observations")
        if not reasons and health == "healthy":
            reasons.append("measured_failures_zero")
        counts = {name: len(values) if values else None for name, values in resources.items()}
        confidence = max(0.0, (len(resources) - len(missing)) / len(resources) - (0.2 if stale else 0))
        return {
            "cluster_id": cluster_id,
            "health": health,
            "reason_codes": reasons,
            "confidence": confidence,
            "data_status": "partial" if missing else "stale" if stale else "complete",
            "observed_at": max(observed_values, default=cluster.get("observed_at")),
            "source_coverage": sorted(
                {
                    source
                    for values in resources.values()
                    for item in values
                    for source in item.get("source_coverage", [])
                }
                | {"kafka_observer"}
            ),
            "missing_inputs": [f"{name}_projection" for name in missing],
            "broker_count": counts["brokers"],
            "topic_count": counts["streams"],
            "partition_count": counts["partitions"],
            "consumer_group_count": counts["consumer_groups"],
            "connector_count": counts["connectors"],
            "healthy_brokers": healthy_brokers,
            "unhealthy_brokers": unhealthy_brokers,
            "under_replicated_partition_count": under_replicated,
            "leaderless_partition_count": leaderless,
            "offline_replica_count": offline,
            "degraded_topic_count": (
                sum(item.get("health") in {"warning", "degraded"} for item in topics) if topics else None
            ),
            "critical_topic_count": sum(item.get("health") == "critical" for item in topics) if topics else None,
            "failed_connector_count": failed_connectors,
            "stale_resource_count": stale,
        }

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
