"""Pure, provider-neutral stream capacity and saturation semantics.

Pressure evidence is deliberately kept separate from observed saturation.  The
module performs no I/O and never treats a missing limit or measurement as zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from packages.streaming.contracts import MeasurementMethod
from packages.streaming.intelligence import PartitionSkew, RetentionForecast


class CapacityState(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    CONSTRAINED = "constrained"
    SATURATED = "saturated"
    THROTTLED = "throttled"
    EXHAUSTION_PREDICTED = "exhaustion_predicted"
    RECOVERING = "recovering"
    INSUFFICIENT_DATA = "insufficient_data"
    STALE = "stale"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class CapacityDimensionName(str, Enum):
    PRODUCER_PRESSURE = "producer_pressure"
    PROVIDER_INGRESS = "provider_ingress_capacity"
    PROVIDER_EGRESS = "provider_egress_capacity"
    PARTITION_SHARD = "partition_or_shard_capacity"
    CONSUMER_PROCESSING = "consumer_processing_capacity"
    CONSUMER_PARALLELISM = "consumer_parallelism_capacity"
    BACKLOG = "backlog_pressure"
    RETENTION = "retention_capacity"
    DELIVERY = "delivery_capacity"
    BROKER_NAMESPACE = "broker_or_namespace_capacity"


class LimitSourceType(str, Enum):
    PROVIDER_API = "provider_api"
    PROVIDER_QUOTA_API = "provider_quota_api"
    PROVIDER_CONFIGURATION = "provider_configuration"
    PROVIDER_DOCUMENTED_VERSIONED_LIMIT = "provider_documented_versioned_limit"
    OPERATOR_DECLARED_LIMIT = "operator_declared_limit"
    CONTRACT_DECLARED_LIMIT = "contract_declared_limit"
    DERIVED = "derived"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapacityLimit:
    value: float
    unit: str
    scope: str
    source: str
    source_type: LimitSourceType
    authoritative: bool
    confidence: float
    provider: str
    messaging_system: str
    evidence_ref: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or self.value <= 0:
            raise ValueError("capacity limit must be finite and positive")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between zero and one")


@dataclass(frozen=True)
class CapacityMeasurement:
    value: float
    unit: str
    method: MeasurementMethod
    observed_at: datetime
    evidence_ref: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or self.value < 0:
            raise ValueError("capacity measurement must be finite and non-negative")


@dataclass(frozen=True)
class CapacityHeadroom:
    absolute: float | None
    ratio: float | None
    utilisation: float | None
    unit: str | None
    reason_codes: tuple[str, ...] = ()


def calculate_headroom(demand: CapacityMeasurement | None, limit: CapacityLimit | None) -> CapacityHeadroom:
    if demand is None:
        return CapacityHeadroom(None, None, None, limit.unit if limit else None, ("demand_missing",))
    if limit is None:
        return CapacityHeadroom(None, None, None, demand.unit, ("limit_missing",))
    if demand.unit != limit.unit:
        return CapacityHeadroom(None, None, None, None, ("unit_mismatch",))
    absolute = limit.value - demand.value
    return CapacityHeadroom(absolute, absolute / limit.value, demand.value / limit.value, limit.unit)


@dataclass(frozen=True)
class CapacityDimension:
    dimension: CapacityDimensionName
    observed_value: float | None
    known_limit: float | None
    utilisation: float | None
    headroom: float | None
    state: CapacityState
    method: str
    confidence: float
    source_coverage: float
    missing_inputs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsumerCapacity:
    arrival_rate: float | None
    processing_rate: float | None
    capacity_balance: float | None
    capacity_deficit: float | None
    net_drain_rate: float | None
    backlog_growth_rate: float | None
    estimated_drain_time: float | None
    convergence: str
    state: str


def evaluate_consumer_capacity(
    arrival_rate: float | None, processing_rate: float | None, backlog: float | None
) -> ConsumerCapacity:
    values = (arrival_rate, processing_rate, backlog)
    if any(value is not None and (not math.isfinite(value) or value < 0) for value in values):
        raise ValueError("consumer capacity inputs must be finite and non-negative")
    if arrival_rate is None or processing_rate is None:
        return ConsumerCapacity(
            arrival_rate, processing_rate, None, None, None, None, None, "unknown", "insufficient_data"
        )
    balance = processing_rate - arrival_rate
    growth = arrival_rate - processing_rate
    convergence = "converging" if balance > 0 else "diverging" if balance < 0 else "stable"
    if backlog and balance <= 0:
        return ConsumerCapacity(
            arrival_rate,
            processing_rate,
            balance,
            max(0.0, -balance),
            balance,
            growth,
            None,
            convergence,
            "not_draining",
        )
    drain = backlog / balance if backlog is not None and backlog > 0 and balance > 0 else 0.0 if backlog == 0 else None
    return ConsumerCapacity(
        arrival_rate,
        processing_rate,
        balance,
        max(0.0, -balance),
        balance,
        growth,
        drain,
        convergence,
        "draining" if drain else "balanced",
    )


@dataclass(frozen=True)
class ParallelismCapacity:
    consumer_count: int | None
    assignable_partitions: int | None
    useful_concurrency: int | None
    ceiling_reached: bool | None
    state: str


def evaluate_parallelism(system: str, consumers: int | None, partitions: int | None) -> ParallelismCapacity:
    if system != "kafka":
        return ParallelismCapacity(consumers, partitions, None, None, "not_applicable")
    if consumers is None or partitions is None:
        return ParallelismCapacity(consumers, partitions, None, None, "unknown")
    if consumers < 0 or partitions < 0:
        raise ValueError("parallelism counts cannot be negative")
    reached = partitions > 0 and consumers >= partitions
    return ParallelismCapacity(
        consumers,
        partitions,
        min(consumers, partitions),
        reached,
        "parallelism_ceiling_reached" if reached else "available",
    )


@dataclass(frozen=True)
class PartitionPressure:
    state: str
    skew: PartitionSkew | None
    hot_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ShardPressure(PartitionPressure):
    pass


@dataclass(frozen=True)
class SaturationSignal:
    signal_type: str
    dimension: CapacityDimensionName
    observed_value: float | None
    threshold_or_limit: float | None
    unit: str | None
    strength: str
    method: str
    first_observed_at: datetime
    last_observed_at: datetime
    confidence: float
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapacityBottleneck:
    candidate: str
    confidence: float
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetentionCapacityPlan:
    forecast: RetentionForecast | None
    earliest_exhaustion_seconds: float | None
    confidence: float
    coverage: float
    missing_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapacityEvidenceCompleteness:
    confidence: float
    source_coverage: float
    missing_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapacityPlanningPolicy:
    watch_utilisation: float = 0.7
    constrained_utilisation: float = 0.9
    stale_after_seconds: int = 300


@dataclass(frozen=True)
class CapacityEvaluation:
    overall_state: CapacityState
    dimensions: tuple[CapacityDimension, ...]
    saturation_signals: tuple[SaturationSignal, ...]
    consumer_capacity: ConsumerCapacity | None
    parallelism: ParallelismCapacity | None
    partition_shard_pressure: PartitionPressure | ShardPressure | None
    retention: RetentionCapacityPlan | None
    bottleneck_candidates: tuple[CapacityBottleneck, ...]
    confidence: float
    missing_inputs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


# A forecast is explicitly a projection, never a measured limit.
@dataclass(frozen=True)
class CapacityForecast:
    dimension: CapacityDimensionName
    predicted_state: CapacityState
    horizon_seconds: float
    confidence: float
    method: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PlanningForecast:
    """Bounded planning projection; values are estimates, never observations."""

    forecast_type: str
    method: str
    horizon_seconds: float
    sample_count: int
    coverage: float
    confidence: float
    lower: float | None
    expected: float | None
    upper: float | None
    missing_inputs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "linear_projection",
        "future_workload_may_differ",
    )


@dataclass(frozen=True)
class RecoveryCapacity:
    required_processing_rate: float
    additional_processing_rate_required: float
    method: str = "derived_required_capacity"


def recovery_capacity(
    arrival_rate: float, backlog: float, processing_rate: float, recovery_target_seconds: float
) -> RecoveryCapacity:
    """Derive rate needed to meet an authoritative recovery target."""
    values = (arrival_rate, backlog, processing_rate, recovery_target_seconds)
    if any(not math.isfinite(value) or value < 0 for value in values) or recovery_target_seconds == 0:
        raise ValueError("recovery capacity inputs must be finite, non-negative, and target must be positive")
    required = arrival_rate + backlog / recovery_target_seconds
    return RecoveryCapacity(required, max(0.0, required - processing_rate))


@dataclass(frozen=True)
class ScalingRecommendation:
    recommendation_type: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: float
    prerequisites: tuple[str, ...]
    expected_effect: str
    limitations: tuple[str, ...]
    advisory_only: bool = True
    automatic_execution: bool = False
    requires_human_review: bool = True


def capacity_recommendations(snapshot: dict[str, object]) -> tuple[ScalingRecommendation, ...]:
    """Produce capability-aware advice from a Part 1 snapshot without mutation."""
    system = str(snapshot.get("messaging_system", "")).lower()
    evidence = tuple(str(ref) for ref in snapshot.get("evidence_refs", ()) or ())
    confidence = float(snapshot.get("confidence", 0.0) or 0.0)
    recommendations: list[ScalingRecommendation] = []

    def add(kind: str, reasons: tuple[str, ...], effect: str, prerequisites: tuple[str, ...] = ()) -> None:
        recommendations.append(
            ScalingRecommendation(
                kind,
                reasons,
                evidence,
                confidence,
                prerequisites + ("human approval required",),
                effect,
                ("advisory estimate only", "validate against provider and workload constraints"),
            )
        )

    consumer = snapshot.get("consumer_capacity") or {}
    if isinstance(consumer, dict) and float(consumer.get("capacity_deficit", 0) or 0) > 0:
        add(
            "increase_consumer_capacity",
            ("consumer_processing_deficit",),
            "Increase processing rate enough to reduce the evidenced deficit.",
        )
    pressure = snapshot.get("partition_shard_pressure") or {}
    hot = isinstance(pressure, dict) and bool(pressure.get("hot_ids"))
    if hot and system == "kafka":
        add("investigate_hot_partition", ("partition_skew_observed",), "Identify key or assignment skew.")
        add(
            "rebalance_partition_keys",
            ("partition_skew_observed",),
            "Improve load distribution if key semantics permit.",
            (
                "ordering impact reviewed",
                "key distribution reviewed",
                "consumer compatibility reviewed",
                "downstream assumptions reviewed",
            ),
        )
    elif hot and system == "kinesis":
        add(
            "investigate_hot_shard",
            ("shard_skew_observed",),
            "Identify partition-key concentration before evaluating resharding.",
        )
    if snapshot.get("retention_risk") is True:
        add(
            "review_retention",
            ("retention_risk",),
            "Evaluate retention and recovery options without changing configuration.",
        )
    if snapshot.get("throttled") is True:
        add(
            "investigate_throttling",
            ("authoritative_throttling_signal",),
            "Confirm provider quota or service throttling.",
        )
    return tuple(recommendations)


def simulate_capacity(
    snapshot: dict[str, object],
    *,
    traffic_multiplier: float = 1.0,
    consumer_processing_multiplier: float = 1.0,
    retention_seconds_override: float | None = None,
    recovery_target_seconds: float | None = None,
    headroom_target_ratio: float = 0.2,
) -> dict[str, object]:
    """Stateless scenario using Part 1 measurements; it cannot alter the snapshot."""
    for value in (traffic_multiplier, consumer_processing_multiplier):
        if not math.isfinite(value) or not 0.1 <= value <= 10:
            raise ValueError("multipliers must be between 0.1 and 10")
    if not 0 <= headroom_target_ratio <= 0.9:
        raise ValueError("headroom target ratio must be between 0 and 0.9")
    consumer = snapshot.get("consumer_capacity") or {}
    consumer = consumer if isinstance(consumer, dict) else {}
    arrival = consumer.get("arrival_rate")
    processing = consumer.get("processing_rate")
    backlog = snapshot.get("backlog", 0)
    scenario_arrival = float(arrival) * traffic_multiplier if arrival is not None else None
    scenario_processing = float(processing) * consumer_processing_multiplier if processing is not None else None
    recovery = None
    if recovery_target_seconds is not None and scenario_arrival is not None and scenario_processing is not None:
        recovery = recovery_capacity(
            scenario_arrival, float(backlog or 0), scenario_processing, recovery_target_seconds
        )
    return {
        "hypothetical": True,
        "observation_status": "not_observed",
        "persisted": False,
        "inputs": {
            "traffic_multiplier": traffic_multiplier,
            "consumer_processing_multiplier": consumer_processing_multiplier,
            "retention_seconds_override": retention_seconds_override,
            "recovery_target_seconds": recovery_target_seconds,
            "headroom_target_ratio": headroom_target_ratio,
        },
        "arrival_rate": scenario_arrival,
        "processing_rate": scenario_processing,
        "capacity_balance": (
            (scenario_processing - scenario_arrival)
            if scenario_arrival is not None and scenario_processing is not None
            else None
        ),
        "required_processing_rate": recovery.required_processing_rate if recovery else None,
        "additional_processing_rate_required": recovery.additional_processing_rate_required if recovery else None,
        "limitations": ["linear bounded scenario", "not observed telemetry", "no infrastructure changes are executed"],
    }
