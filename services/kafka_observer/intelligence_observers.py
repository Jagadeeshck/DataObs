"""Allowlisted, bounded historical evidence adapters for Stream Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from packages.streaming.intelligence import DetectorDefinition, EvidenceSeries, TimeSeriesPoint


@dataclass(frozen=True)
class EvidenceBinding:
    index: str
    resource_field: str
    metric_field: str


# These are storage contracts, not client-selectable Elasticsearch fields.
_INDEX = {
    "kafka_cluster": "metrics-dataobs.kafka_cluster-*",
    "topic": "metrics-dataobs.kafka_topic-*",
    "consumer_group": "metrics-dataobs.kafka_consumer_group-*",
    "connector": "metrics-dataobs.kafka_connector-*",
    "pathway": "metrics-dataobs.pathway-*",
}
_RESOURCE_FIELD = {
    "kafka_cluster": "cluster_id",
    "topic": "topic_id",
    "consumer_group": "consumer_group_id",
    "connector": "connector_id",
    "pathway": "pathway_id",
}
_METRIC_FIELD = {
    "under_replicated_partitions": "under_replicated_partitions",
    "offline_partitions": "offline_partitions",
    "broker_availability": "availability",
    "throughput": "throughput",
    "producer_throughput": "producer_rate",
    "partition_throughput_skew": "partition_throughput",
    "partition_size_skew": "partition_size_bytes",
    "message_size": "average_message_size_bytes",
    "error_rate": "error_rate",
    "retry_rate": "retry_rate",
    "dlq_growth": "dlq_count",
    "replication": "replication_health",
    "total_lag": "total_lag",
    "maximum_partition_lag": "maximum_partition_lag",
    "lag_growth": "lag_growth_rate",
    "consumer_throughput": "consume_rate",
    "estimated_drain_time": "estimated_drain_time_seconds",
    "offset_progress": "offset_progress",
    "partition_lag_skew": "partition_lag",
    "retention_exhaustion": "retention_exhaustion_seconds",
    "failed_tasks": "failed_tasks",
    "running_task_ratio": "running_task_ratio",
    "restart_pattern": "restart_count",
    "backlog": "backlog",
    "task_imbalance": "task_imbalance",
    "latency_p95": "latency_p95_ms",
    "latency_p99": "latency_p99_ms",
    "reliability": "reliability",
    "availability": "availability",
    "retention_risk": "retention_risk_score",
    "source_coverage": "source_coverage",
}


class HistoricalEvidenceObserver:
    MAX_POINTS = 5000

    def __init__(self, es: Any, *, normal_max_days: int = 7, seasonal_max_days: int = 35, timeout: str = "5s"):
        self.es = es
        self.normal_max_days = min(max(normal_max_days, 1), 7)
        self.seasonal_max_days = min(max(seasonal_max_days, self.normal_max_days), 35)
        self.timeout = timeout

    @staticmethod
    def binding(definition: DetectorDefinition) -> EvidenceBinding:
        if definition.resource_type not in _INDEX:
            raise ValueError("unsupported resource type")
        freshness = definition.metric == "observation_freshness"
        field = "observation_age_seconds" if freshness else _METRIC_FIELD.get(definition.metric)
        if not field:
            raise ValueError("metric has no authoritative historical binding")
        return EvidenceBinding(_INDEX[definition.resource_type], _RESOURCE_FIELD[definition.resource_type], field)

    def __call__(
        self, definition: DetectorDefinition, start: datetime, end: datetime, *, maximum_points: int | None = None
    ) -> EvidenceSeries:
        start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        if start >= end:
            raise ValueError("historical range must be positive")
        maximum_range = timedelta(
            days=self.seasonal_max_days if definition.seasonal_mode != "none" else self.normal_max_days
        )
        if end - start > maximum_range:
            raise ValueError("historical range exceeds configured bound")
        points = min(max(maximum_points or definition.maximum_sample_count, 1), self.MAX_POINTS)
        binding = self.binding(definition)
        interval_ms = max(1000, int((end - start).total_seconds() * 1000 / points))
        response = self.es.search(
            index=binding.index,
            size=0,
            timeout=self.timeout,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": definition.tenant_id}},
                        {"term": {"environment": definition.environment}},
                        {"term": {binding.resource_field: definition.resource_id}},
                        {"range": {"@timestamp": {"gte": start.isoformat(), "lte": end.isoformat()}}},
                    ]
                }
            },
            aggs={
                "series": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "fixed_interval": f"{interval_ms}ms",
                        "min_doc_count": 0,
                        "extended_bounds": {"min": start.isoformat(), "max": end.isoformat()},
                    },
                    "aggs": {
                        "value": {"avg": {"field": binding.metric_field}},
                        "quality": {"terms": {"field": "evidence_status", "size": 1}},
                    },
                }
            },
            source=False,
        )
        buckets = response["aggregations"]["series"]["buckets"][:points]
        series: list[TimeSeriesPoint] = []
        for bucket in buckets:
            value = bucket.get("value", {}).get("value")
            quality = bucket.get("quality", {}).get("buckets", [])
            status = (
                quality[0]["key"]
                if quality and quality[0]["key"] in {"measured", "partial", "estimated", "inferred", "stale"}
                else ("measured" if value is not None else "missing")
            )
            # Missing/stale evidence must not carry a value into the algorithm.
            if status in {"missing", "stale"}:
                value = None
            series.append(
                TimeSeriesPoint(
                    datetime.fromtimestamp(bucket["key"] / 1000, timezone.utc),
                    value,
                    status,
                    f"{binding.index}:{bucket['key']}",
                )
            )
        return EvidenceSeries(tuple(series), len(buckets), binding.index)
