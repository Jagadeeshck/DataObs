"""Pure Team 1 stream/pathway reliability semantics.

This module deliberately has no Elasticsearch or web dependencies.  Workers load the
previous projection, call :func:`evaluate`, persist the returned evidence, and only
then advance their checkpoint.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class Status(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    BREACHING = "breaching"
    RECOVERING = "recovering"
    NO_DATA = "no_data"
    STALE = "stale"
    ERROR = "error"
    DISABLED = "disabled"


Operator = Literal["gt", "gte", "lt", "lte"]
MissingPolicy = Literal["no_data", "breach", "ignore"]

CAPABILITIES: dict[str, tuple[str, ...]] = {
    "kafka_cluster": ("under_replicated_partitions", "offline_partitions", "observation_freshness"),
    "topic": (
        "producer_throughput_floor",
        "under_replicated_partitions",
        "offline_partitions",
        "observation_freshness",
    ),
    "consumer_group": (
        "consumer_lag",
        "maximum_partition_lag",
        "lag_growth_rate",
        "estimated_drain_time",
        "consumer_throughput_floor",
        "retention_risk",
        "data_loss_suspected",
        "observation_freshness",
    ),
    "connector": ("connector_failed_tasks", "connector_running_task_ratio", "observation_freshness"),
    "pathway": (
        "pathway_latency_p95",
        "pathway_latency_p99",
        "pathway_reliability",
        "pathway_availability",
        "pathway_backlog",
        "pathway_retention_risk",
        "pathway_observation_freshness",
        "pathway_source_coverage",
    ),
    "kinesis_stream": (
        "observation_freshness",
        "availability",
        "throughput_floor",
        "throughput_ceiling",
        "lag_age",
        "throttling_rate",
    ),
    "sqs_queue": (
        "observation_freshness",
        "availability",
        "backlog_count",
        "backlog_age",
        "drain_time",
        "dead_letter_growth",
    ),
    "rabbitmq_queue": (
        "observation_freshness",
        "availability",
        "backlog_count",
        "unacknowledged_count",
        "retry_or_redelivery_rate",
        "consumer_health",
    ),
    "pubsub_subscription": (
        "observation_freshness",
        "backlog_count",
        "backlog_bytes",
        "backlog_age",
        "dead_letter_growth",
        "subscription_health",
    ),
    "event_hub": (
        "observation_freshness",
        "availability",
        "throughput_floor",
        "throughput_ceiling",
        "throttling_rate",
        "server_error_rate",
    ),
    "service_bus_queue": (
        "observation_freshness",
        "availability",
        "backlog_count",
        "dead_letter_growth",
        "throttling_rate",
        "server_error_rate",
    ),
    "service_bus_subscription": (
        "observation_freshness",
        "backlog_count",
        "dead_letter_growth",
        "subscription_health",
        "server_error_rate",
    ),
}


@dataclass(frozen=True)
class Definition:
    id: str
    tenant_id: str
    environment: str
    resource_type: str
    resource_id: str
    metric: str
    operator: Operator
    threshold: float
    evaluation_window_seconds: int
    evaluation_interval_seconds: int = 60
    required_consecutive_breaches: int = 2
    recovery_evaluation_count: int = 2
    missing_data_policy: MissingPolicy = "no_data"
    enabled: bool = False
    owner: str = "unassigned"
    revision: int = 1
    schema_version: str = "v1"

    def __post_init__(self) -> None:
        if not self.id or len(self.id) > 128 or not self.resource_id or len(self.resource_id) > 512:
            raise ValueError("definition and resource identifiers must be non-empty and bounded")
        if not self.tenant_id or len(self.tenant_id) > 128 or not self.environment or len(self.environment) > 128:
            raise ValueError("tenant and environment must be non-empty and bounded")
        if not self.owner or len(self.owner) > 256:
            raise ValueError("owner must be non-empty and bounded")
        if self.operator not in {"gt", "gte", "lt", "lte"}:
            raise ValueError("operator is not supported")
        if self.missing_data_policy not in {"no_data", "breach", "ignore"}:
            raise ValueError("missing-data policy is not supported")
        if isinstance(self.threshold, bool) or not math.isfinite(self.threshold):
            raise ValueError("threshold must be finite")
        if self.metric not in CAPABILITIES.get(self.resource_type, ()):
            raise ValueError("metric is not supported for resource type")
        if not 1 <= self.evaluation_window_seconds <= 31 * 86400:
            raise ValueError("evaluation window must be between 1 second and 31 days")
        if not 1 <= self.evaluation_interval_seconds <= self.evaluation_window_seconds:
            raise ValueError("evaluation interval must be bounded by the window")
        if self.required_consecutive_breaches < 1 or self.recovery_evaluation_count < 1:
            raise ValueError("consecutive evaluation counts must be positive")


@dataclass(frozen=True)
class PreviousState:
    status: Status = Status.NO_DATA
    consecutive_breaches: int = 0
    consecutive_recoveries: int = 0
    first_breach_at: datetime | None = None


@dataclass(frozen=True)
class Observation:
    value: float | None
    observed_at: datetime | None
    unit: str
    evidence_type: str
    confidence: float | None = None
    source_coverage: float | None = None
    latency_method: Literal["trace_derived", "edge_estimate", "unavailable"] | None = None
    missing_inputs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Evaluation:
    evaluation_id: str
    definition_id: str
    status: Status
    previous_status: Status
    observed_value: float | None
    consecutive_breaches: int
    consecutive_recoveries: int
    first_breach_at: datetime | None
    last_breach_at: datetime | None
    breach_duration_seconds: int | None
    reason_codes: tuple[str, ...]
    observed_at: datetime | None
    evaluated_at: datetime
    latency_method: str | None
    missing_inputs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evidence_type: str
    confidence: float | None
    source_coverage: float | None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def deterministic_evaluation_id(definition: Definition, window_end: datetime) -> str:
    end = window_end.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    raw = f"{definition.tenant_id}\0{definition.environment}\0{definition.id}\0{definition.revision}\0{end}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _breaches(value: float, threshold: float, operator: Operator) -> bool:
    return {"gt": value > threshold, "gte": value >= threshold, "lt": value < threshold, "lte": value <= threshold}[
        operator
    ]


def evaluate(definition: Definition, observation: Observation, previous: PreviousState, now: datetime) -> Evaluation:
    now = now.astimezone(timezone.utc)
    evaluation_id = deterministic_evaluation_id(definition, now)
    common = dict(
        evaluation_id=evaluation_id,
        definition_id=definition.id,
        previous_status=previous.status,
        observed_value=observation.value,
        observed_at=observation.observed_at,
        evaluated_at=now,
        latency_method=observation.latency_method,
        missing_inputs=observation.missing_inputs,
        evidence_refs=observation.evidence_refs,
        evidence_type=observation.evidence_type,
        confidence=observation.confidence,
        source_coverage=observation.source_coverage,
    )
    if not definition.enabled:
        return Evaluation(
            status=Status.DISABLED,
            consecutive_breaches=0,
            consecutive_recoveries=0,
            first_breach_at=None,
            last_breach_at=None,
            breach_duration_seconds=None,
            reason_codes=("definition_disabled",),
            **common,
        )
    missing = observation.value is None or observation.observed_at is None
    stale = (
        not missing
        and (now - observation.observed_at.astimezone(timezone.utc)).total_seconds()
        > definition.evaluation_window_seconds
    )
    if stale:
        return Evaluation(
            status=Status.STALE,
            consecutive_breaches=previous.consecutive_breaches,
            consecutive_recoveries=0,
            first_breach_at=previous.first_breach_at,
            last_breach_at=None,
            breach_duration_seconds=None,
            reason_codes=("observation_stale",),
            **common,
        )
    if missing and definition.missing_data_policy != "breach":
        status = previous.status if definition.missing_data_policy == "ignore" else Status.NO_DATA
        return Evaluation(
            status=status,
            consecutive_breaches=previous.consecutive_breaches,
            consecutive_recoveries=previous.consecutive_recoveries,
            first_breach_at=previous.first_breach_at,
            last_breach_at=None,
            breach_duration_seconds=None,
            reason_codes=(
                ("missing_data_ignored",) if definition.missing_data_policy == "ignore" else ("missing_evidence",)
            ),
            **common,
        )
    breached = missing or _breaches(observation.value, definition.threshold, definition.operator)  # type: ignore[arg-type]
    if breached:
        count = previous.consecutive_breaches + 1
        first = previous.first_breach_at or now
        status = Status.BREACHING if count >= definition.required_consecutive_breaches else Status.WARNING
        return Evaluation(
            status=status,
            consecutive_breaches=count,
            consecutive_recoveries=0,
            first_breach_at=first,
            last_breach_at=now,
            breach_duration_seconds=int((now - first).total_seconds()),
            reason_codes=(("missing_data_breach",) if missing else ("threshold_breached",)),
            **common,
        )
    recoveries = previous.consecutive_recoveries + 1 if previous.status in {Status.BREACHING, Status.RECOVERING} else 0
    recovering = (
        previous.status in {Status.BREACHING, Status.RECOVERING} and recoveries < definition.recovery_evaluation_count
    )
    return Evaluation(
        status=Status.RECOVERING if recovering else Status.HEALTHY,
        consecutive_breaches=0,
        consecutive_recoveries=recoveries if recovering else 0,
        first_breach_at=previous.first_breach_at if recovering else None,
        last_breach_at=None,
        breach_duration_seconds=None,
        reason_codes=(("recovery_pending",) if recovering else ("objective_met",)),
        **common,
    )
