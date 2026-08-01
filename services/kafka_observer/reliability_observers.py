"""Bounded observation adapter over existing Team 1 current projections."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from packages.streaming.reliability import Definition, Observation

ALIASES = {
    "kafka_cluster": "dataobs-kafka-clusters-current-v1-read",
    "topic": "dataobs-streams-current-v1-read",
    "consumer_group": "dataobs-consumer-groups-current-v1-read",
    "connector": "dataobs-stream-connectors-current-v1-read",
    "pathway": "dataobs-pathways-current-v1-read",
}
FIELDS = {
    "under_replicated_partitions": "under_replicated_partitions",
    "offline_partitions": "offline_partitions",
    "producer_throughput_floor": "producer_throughput",
    "consumer_lag": "total_lag",
    "maximum_partition_lag": "maximum_partition_lag",
    "lag_growth_rate": "lag_growth_rate",
    "estimated_drain_time": "estimated_drain_time_seconds",
    "consumer_throughput_floor": "consumer_throughput",
    "retention_risk": "retention_risk_score",
    "data_loss_suspected": "data_loss_suspected",
    "connector_failed_tasks": "failed_tasks",
    "connector_running_task_ratio": "running_task_ratio",
    "pathway_latency_p95": "latency_p95_ms",
    "pathway_latency_p99": "latency_p99_ms",
    "pathway_reliability": "reliability",
    "pathway_availability": "availability",
    "pathway_backlog": "backlog",
    "pathway_retention_risk": "retention_risk_score",
    "pathway_source_coverage": "source_coverage",
}


class ReliabilityObserver:
    def __init__(self, es: Any):
        self.es = es

    def __call__(self, definition: Definition, start: datetime, end: datetime) -> Observation:
        field = FIELDS.get(definition.metric)
        freshness = definition.metric in {"observation_freshness", "pathway_observation_freshness"}
        includes = ["observed_at", "evidence_type", "confidence", "source_coverage", "latency_method", "missing_inputs"]
        if field:
            includes.append(field)
        result = self.es.search(
            index=ALIASES[definition.resource_type],
            size=1,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": definition.tenant_id}},
                        {"term": {"environment": definition.environment}},
                        {"term": {"resource_id": definition.resource_id}},
                        {"range": {"observed_at": {"gte": start.isoformat(), "lte": end.isoformat()}}},
                    ]
                }
            },
            sort=[{"observed_at": "desc"}],
            source_includes=includes,
        )
        hits = result["hits"]["hits"]
        if not hits:
            return Observation(None, None, self._unit(definition.metric), "unavailable", missing_inputs=("projection",))
        source = hits[0]["_source"]
        observed = datetime.fromisoformat(source["observed_at"].replace("Z", "+00:00"))
        value = (end - observed).total_seconds() if freshness else source.get(field) if field else None
        latency = (
            source.get("latency_method")
            if definition.resource_type == "pathway" and "latency" in definition.metric
            else None
        )
        if latency not in {None, "trace_derived", "edge_estimate", "unavailable"}:
            latency = "unavailable"
        return Observation(
            value,
            observed,
            self._unit(definition.metric),
            source.get("evidence_type", "projection"),
            source.get("confidence"),
            source.get("source_coverage"),
            latency,
            tuple(source.get("missing_inputs", ())),
            (f"{ALIASES[definition.resource_type]}:{hits[0]['_id']}",),
        )

    @staticmethod
    def _unit(metric: str) -> str:
        if "latency" in metric or "drain_time" in metric or "freshness" in metric:
            return "seconds" if "latency" not in metric else "milliseconds"
        if "ratio" in metric or "coverage" in metric or metric in {"pathway_reliability", "pathway_availability"}:
            return "ratio"
        if "throughput" in metric or "growth_rate" in metric:
            return "records_per_second"
        return "count"
