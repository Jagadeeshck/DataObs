"""Dependency-free, explainable stream intelligence contracts and algorithms.

Missing evidence is never converted to zero.  All calculations are deterministic
and deliberately avoid claims of causation or statistically precise confidence.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Sequence


class DetectorState(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    ANOMALOUS = "anomalous"
    SEVERE = "severe"
    RECOVERING = "recovering"
    INSUFFICIENT_DATA = "insufficient_data"
    STALE = "stale"
    ERROR = "error"
    DISABLED = "disabled"


class ForecastState(str, Enum):
    SAFE = "safe"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTION_PREDICTED = "exhaustion_predicted"
    DATA_LOSS_SUSPECTED = "data_loss_suspected"
    NOT_DRAINING = "not_draining"
    INSUFFICIENT_DATA = "insufficient_data"
    STALE = "stale"
    ERROR = "error"


METHODS = frozenset(
    {
        "robust_zscore",
        "median_absolute_deviation",
        "ewma_deviation",
        "relative_change",
        "rate_of_change",
        "trend_forecast",
        "seasonal_bucket",
        "partition_skew",
        "retention_exhaustion",
        "failure_pattern",
    }
)
Direction = Literal["high", "low", "both"]
PointStatus = Literal["measured", "missing", "partial", "stale", "estimated", "inferred"]


CAPABILITIES = {
    "kafka_cluster": frozenset(
        {
            "under_replicated_partitions",
            "offline_partitions",
            "broker_availability",
            "throughput",
            "observation_freshness",
        }
    ),
    "topic": frozenset(
        {
            "producer_throughput",
            "partition_throughput_skew",
            "partition_size_skew",
            "message_size",
            "error_rate",
            "retry_rate",
            "dlq_growth",
            "replication",
            "observation_freshness",
        }
    ),
    "consumer_group": frozenset(
        {
            "total_lag",
            "maximum_partition_lag",
            "lag_growth",
            "consumer_throughput",
            "estimated_drain_time",
            "offset_progress",
            "partition_lag_skew",
            "retention_exhaustion",
            "observation_freshness",
        }
    ),
    "connector": frozenset(
        {
            "failed_tasks",
            "running_task_ratio",
            "restart_pattern",
            "throughput",
            "error_rate",
            "backlog",
            "task_imbalance",
            "observation_freshness",
        }
    ),
    "pathway": frozenset(
        {
            "latency_p95",
            "latency_p99",
            "throughput",
            "backlog",
            "error_rate",
            "retry_rate",
            "dlq_growth",
            "reliability",
            "availability",
            "retention_risk",
            "source_coverage",
            "observation_freshness",
        }
    ),
    "kinesis_stream": frozenset({"iterator_age", "throughput", "throttling", "observation_freshness"}),
    "sqs_queue": frozenset(
        {"backlog", "oldest_message_age", "dlq_growth", "consumption_rate", "observation_freshness"}
    ),
    "rabbitmq_queue": frozenset(
        {"ready_messages", "unacknowledged_messages", "redelivery_rate", "consumer_count", "observation_freshness"}
    ),
    "pubsub_subscription": frozenset(
        {"backlog", "backlog_bytes", "oldest_unacked_age", "delivery_latency", "dlq_growth", "observation_freshness"}
    ),
    "event_hub": frozenset({"incoming", "outgoing", "throttling", "server_errors", "observation_freshness"}),
    "service_bus_queue": frozenset(
        {"active_messages", "dlq_growth", "server_errors", "throughput", "observation_freshness"}
    ),
}


@dataclass(frozen=True)
class DetectorDefinition:
    detector_id: str
    tenant_id: str
    environment: str
    resource_type: str
    resource_id: str
    metric: str
    method: str
    direction: Direction
    baseline_window_seconds: int
    evaluation_window_seconds: int
    evaluation_interval_seconds: int
    minimum_sample_count: int = 8
    maximum_sample_count: int = 1000
    sensitivity: float = 3.5
    warning_threshold: float = 3.5
    severe_threshold: float = 6.0
    required_consecutive_anomalies: int = 2
    recovery_evaluation_count: int = 2
    missing_data_policy: str = "insufficient_data"
    seasonal_mode: str = "none"
    forecast_horizon_seconds: int | None = None
    enabled: bool = False
    owner: str = "unassigned"
    revision: int = 1
    created_actor: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_actor: str = "system"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_evaluation_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "v1"

    def __post_init__(self) -> None:
        if self.resource_type not in CAPABILITIES or self.metric not in CAPABILITIES[self.resource_type]:
            raise ValueError("unsupported detector resource/metric combination")
        if self.method not in METHODS or self.direction not in {"high", "low", "both"}:
            raise ValueError("unsupported detector method or direction")
        if not 3 <= self.minimum_sample_count <= self.maximum_sample_count <= 10000:
            raise ValueError("sample bounds are invalid")
        if self.required_consecutive_anomalies < 1 or self.recovery_evaluation_count < 1:
            raise ValueError("transition counts must be positive")
        if not all((self.detector_id, self.tenant_id, self.environment, self.resource_id, self.owner)):
            raise ValueError("detector identity and ownership are required")


@dataclass(frozen=True)
class TimeSeriesPoint:
    timestamp: datetime
    value: float | None
    status: PointStatus = "measured"
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        if self.status in {"missing", "stale"} and self.value is not None:
            raise ValueError("missing/stale points cannot carry a measured value")
        if self.value is not None and (isinstance(self.value, bool) or not math.isfinite(self.value)):
            raise ValueError("point values must be finite")


@dataclass(frozen=True)
class EvidenceSeries:
    points: tuple[TimeSeriesPoint, ...]
    expected_buckets: int
    source: str


@dataclass(frozen=True)
class ExpectedRange:
    lower: float
    expected: float
    upper: float


@dataclass(frozen=True)
class Baseline:
    median: float
    mad: float
    expected_range: ExpectedRange
    sample_count: int
    data_coverage: float
    method: str = "median_absolute_deviation"
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DetectorPreviousState:
    state: DetectorState = DetectorState.INSUFFICIENT_DATA
    consecutive_anomalies: int = 0
    consecutive_recoveries: int = 0


@dataclass(frozen=True)
class AnomalyEvaluation:
    state: DetectorState
    method: str
    observed_value: float | None
    expected_value: float | None
    expected_range: ExpectedRange | None
    deviation_score: float | None
    sample_count: int
    data_coverage: float
    consecutive_anomalies: int
    consecutive_recoveries: int
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class RetentionForecast:
    current_lag: float
    current_backlog_age_seconds: float | None
    current_backlog_bytes: float | None
    production_rate: float
    consumption_rate: float
    net_backlog_growth_rate: float
    lag_slope: float | None
    backlog_age_slope: float | None
    byte_growth_slope: float | None
    estimated_drain_time_seconds: float | None
    time_retention_exhaustion_seconds: float | None
    byte_retention_exhaustion_seconds: float | None
    earliest_exhaustion_seconds: float | None
    forecast_horizon_seconds: int
    lower_estimate_seconds: float | None
    expected_estimate_seconds: float | None
    upper_estimate_seconds: float | None
    state: ForecastState
    sample_count: int
    data_coverage: float
    confidence: float
    missing_inputs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...]
    evaluated_at: datetime
    schema_version: str = "v1"


@dataclass(frozen=True)
class PartitionSkew:
    median: float
    maximum: float
    minimum: float
    skew_ratio: float | None
    robust_deviation: float
    affected_partition_ids: tuple[int, ...]
    affected_partition_count: int
    total_partition_count: int
    source_coverage: float
    confidence: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ChangeOverlay:
    change_type: str
    changed_resource: str
    changed_at: datetime
    summary: str
    source: str
    evidence_reference: str
    time_distance_seconds: int
    confidence: float
    data_status: str


@dataclass(frozen=True)
class FailureCandidate:
    candidate_id: str
    classification: str
    tenant_id: str
    environment: str
    resource_type: str
    resource_id: str
    partition: int | None
    consumer_group_or_connector: str | None
    first_observed_at: datetime
    latest_observed_at: datetime
    retry_rate: float | None
    error_rate: float | None
    dlq_growth: float | None
    offset_progress_state: str
    error_fingerprint: str | None
    overlay_references: tuple[str, ...]
    confidence: float
    source_coverage: float
    reason_codes: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass
class DetectorRuntimeHealth:
    configured: bool
    worker_id: str
    worker_version: str
    heartbeat_at: datetime | None = None
    lease_status: str = "unknown"
    detectors_due: int = 0
    evaluated: int = 0
    skipped: int = 0
    failed: int = 0
    insufficient_data_count: int = 0
    forecasts_produced: int = 0
    candidates_produced: int = 0
    pending_reconciliations: int = 0
    elasticsearch_dependency_state: str = "unknown"


def _quantile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def robust_baseline(series: EvidenceSeries, maximum_points: int = 1000) -> Baseline:
    valid = [
        p.value
        for p in sorted(series.points, key=lambda p: p.timestamp)
        if p.value is not None and p.status not in {"missing", "stale"}
    ]
    valid = valid[-max(1, min(maximum_points, 10000)) :]
    if not valid:
        raise ValueError("insufficient evidence for baseline")
    median = statistics.median(valid)
    deviations = [abs(value - median) for value in valid]
    mad = statistics.median(deviations)
    coverage = min(1.0, len(valid) / max(1, series.expected_buckets))
    return Baseline(
        median,
        mad,
        ExpectedRange(_quantile(valid, 0.1), median, _quantile(valid, 0.9)),
        len(valid),
        coverage,
        reason_codes=(("constant_series",) if mad == 0 else ()),
    )


def evaluate_anomaly(
    definition: DetectorDefinition, series: EvidenceSeries, previous: DetectorPreviousState = DetectorPreviousState()
) -> AnomalyEvaluation:
    if not definition.enabled:
        return AnomalyEvaluation(
            DetectorState.DISABLED, definition.method, None, None, None, None, 0, 0, 0, 0, ("detector_disabled",)
        )
    try:
        baseline = robust_baseline(
            EvidenceSeries(series.points[:-1], max(0, series.expected_buckets - 1), series.source),
            definition.maximum_sample_count,
        )
    except ValueError:
        return AnomalyEvaluation(
            DetectorState.INSUFFICIENT_DATA,
            definition.method,
            None,
            None,
            None,
            None,
            0,
            0,
            0,
            0,
            ("minimum_samples_not_met",),
        )
    current = sorted(series.points, key=lambda p: p.timestamp)[-1]
    if baseline.sample_count < definition.minimum_sample_count or current.value is None:
        return AnomalyEvaluation(
            DetectorState.INSUFFICIENT_DATA,
            definition.method,
            current.value,
            baseline.median,
            baseline.expected_range,
            None,
            baseline.sample_count,
            baseline.data_coverage,
            0,
            0,
            ("minimum_samples_not_met",),
        )
    delta = current.value - baseline.median
    score = (abs(delta) / (1.4826 * baseline.mad)) if baseline.mad else (0.0 if delta == 0 else abs(delta))
    directional = (
        definition.direction == "both"
        or (definition.direction == "high" and delta > 0)
        or (definition.direction == "low" and delta < 0)
    )
    abnormal = directional and score >= definition.warning_threshold
    severe = directional and score >= definition.severe_threshold
    if abnormal:
        count = previous.consecutive_anomalies + 1
        state = (
            DetectorState.SEVERE
            if severe
            else (
                DetectorState.ANOMALOUS if count >= definition.required_consecutive_anomalies else DetectorState.WATCH
            )
        )
        reasons = ("constant_baseline_change",) if baseline.mad == 0 else ("robust_deviation_exceeded",)
        return AnomalyEvaluation(
            state,
            definition.method,
            current.value,
            baseline.median,
            baseline.expected_range,
            score,
            baseline.sample_count,
            baseline.data_coverage,
            count,
            0,
            reasons,
        )
    recoveries = (
        previous.consecutive_recoveries + 1
        if previous.state in {DetectorState.ANOMALOUS, DetectorState.SEVERE, DetectorState.RECOVERING}
        else 0
    )
    state = (
        DetectorState.RECOVERING
        if recoveries and recoveries < definition.recovery_evaluation_count
        else DetectorState.NORMAL
    )
    return AnomalyEvaluation(
        state,
        definition.method,
        current.value,
        baseline.median,
        baseline.expected_range,
        score,
        baseline.sample_count,
        baseline.data_coverage,
        0,
        recoveries,
        ("within_expected_range",),
    )


def ewma(values: Sequence[float], alpha: float = 0.3, warmup: int = 3) -> tuple[float, float]:
    if not 0.01 <= alpha <= 1 or len(values) < warmup or any(not math.isfinite(v) for v in values):
        raise ValueError("invalid EWMA evidence")
    expected = values[0]
    deviations = []
    for value in values[1:]:
        deviations.append(abs(value - expected))
        expected = alpha * value + (1 - alpha) * expected
    return expected, statistics.median(deviations)


def relative_change(current: float, baseline: float) -> tuple[float, str]:
    if baseline == 0:
        return current - baseline, "zero_baseline_absolute_change"
    return (current - baseline) / abs(baseline), "relative_change"


def partition_skew(
    values: dict[int, float | None], expected_partitions: int, cap: int = 20, threshold: float = 3.5
) -> PartitionSkew:
    measured = {p: v for p, v in values.items() if v is not None and math.isfinite(v)}
    if not measured:
        raise ValueError("partition evidence is unavailable")
    vals = list(measured.values())
    med = statistics.median(vals)
    mad = statistics.median(abs(v - med) for v in vals)
    scored = [
        (abs(v - med) / (1.4826 * mad) if mad else (0 if v == med else abs(v - med)), p) for p, v in measured.items()
    ]
    affected = tuple(sorted(p for score, p in scored if score >= threshold))[: max(0, min(cap, 100))]
    reasons = (
        ("single_partition_not_skewed",)
        if expected_partitions <= 1
        else (("partition_skew_detected",) if affected else ("partitions_balanced",))
    )
    if expected_partitions <= 1:
        affected = ()
    return PartitionSkew(
        med,
        max(vals),
        min(vals),
        (max(vals) / med if med != 0 else None),
        max((s for s, _ in scored), default=0),
        affected,
        len(affected),
        expected_partitions,
        len(measured) / max(1, expected_partitions),
        min(1.0, len(measured) / max(1, expected_partitions)),
        reasons,
    )


def retention_forecast(
    *,
    current_lag: float,
    production_rates: Sequence[float],
    consumption_rates: Sequence[float],
    horizon_seconds: int,
    backlog_age_seconds: float | None = None,
    retention_seconds: float | None = None,
    backlog_bytes: float | None = None,
    retention_bytes: float | None = None,
    authoritative_loss_evidence: bool = False,
    evidence_references: tuple[str, ...] = (),
    now: datetime | None = None,
) -> RetentionForecast:
    if not production_rates or not consumption_rates:
        raise ValueError("rate evidence is required")
    production = statistics.median(production_rates[-20:])
    consumption = statistics.median(consumption_rates[-20:])
    growth = production - consumption
    drain = (
        current_lag / (consumption - production)
        if consumption > production and current_lag > 0
        else (0.0 if current_lag == 0 else None)
    )
    time_exhaustion = (
        ((retention_seconds - backlog_age_seconds) / max(growth / current_lag, 1e-12))
        if retention_seconds is not None and backlog_age_seconds is not None and current_lag > 0 and growth > 0
        else None
    )
    byte_exhaustion = (
        ((retention_bytes - backlog_bytes) / growth)
        if retention_bytes is not None and backlog_bytes is not None and growth > 0
        else None
    )
    estimates = [v for v in (time_exhaustion, byte_exhaustion) if v is not None]
    earliest = min(estimates) if estimates else None
    missing = tuple(
        name
        for name, value in (
            ("record_age", backlog_age_seconds),
            ("retention_time", retention_seconds),
            ("backlog_bytes", backlog_bytes),
            ("retention_bytes", retention_bytes),
        )
        if value is None
    )
    if authoritative_loss_evidence:
        state = ForecastState.DATA_LOSS_SUSPECTED
    elif earliest is not None and earliest <= 0:
        state = ForecastState.EXHAUSTION_PREDICTED
    elif earliest is not None and earliest <= horizon_seconds * 0.25:
        state = ForecastState.CRITICAL
    elif earliest is not None and earliest <= horizon_seconds:
        state = ForecastState.WARNING
    elif drain is None:
        state = ForecastState.NOT_DRAINING
    else:
        state = ForecastState.SAFE
    spread = earliest * 0.2 if earliest is not None and len(production_rates) >= 3 else None
    lower_estimate = max(0, earliest - spread) if earliest is not None and spread is not None else None
    upper_estimate = earliest + spread if earliest is not None and spread is not None else None
    return RetentionForecast(
        current_lag,
        backlog_age_seconds,
        backlog_bytes,
        production,
        consumption,
        growth,
        None,
        None,
        None,
        drain,
        time_exhaustion,
        byte_exhaustion,
        earliest,
        max(60, min(horizon_seconds, 31 * 86400)),
        lower_estimate,
        earliest,
        upper_estimate,
        state,
        min(len(production_rates), len(consumption_rates)),
        1.0,
        min(1.0, min(len(production_rates), len(consumption_rates)) / 8),
        missing,
        (
            ("authoritative_offset_outside_retention",)
            if authoritative_loss_evidence
            else (("effective_drain_rate_not_positive",) if drain is None else ("forecast_calculated",))
        ),
        evidence_references,
        (now or datetime.now(timezone.utc)).astimezone(timezone.utc),
    )


def safe_error_fingerprint(classifications: Sequence[str]) -> str | None:
    normalized = sorted(
        {"".join(ch for ch in item.lower() if ch.isalnum() or ch in "_-")[:64] for item in classifications if item}
    )
    return hashlib.sha256("\0".join(normalized).encode()).hexdigest()[:24] if normalized else None


def classify_failure_candidate(
    *,
    tenant_id: str,
    environment: str,
    resource_type: str,
    resource_id: str,
    observed_at: datetime,
    retry_rate: float | None = None,
    error_rate: float | None = None,
    dlq_growth: float | None = None,
    offset_stalled: bool = False,
    classifications: Sequence[str] = (),
    partition: int | None = None,
    subject: str | None = None,
    evidence_references: tuple[str, ...] = (),
    overlay_references: tuple[str, ...] = (),
) -> FailureCandidate | None:
    reasons = tuple(
        code
        for present, code in (
            (retry_rate is not None and retry_rate > 0, "retry_increase"),
            (error_rate is not None and error_rate > 0, "processing_errors"),
            (dlq_growth is not None and dlq_growth > 0, "dlq_growth"),
            (offset_stalled, "offset_progress_stalled"),
            (bool(classifications), "repeated_failure_fingerprint"),
        )
        if present
    )
    if len(reasons) < 2:
        return None
    raw = f"{tenant_id}\0{environment}\0{resource_type}\0{resource_id}\0{partition}\0{safe_error_fingerprint(classifications)}"
    missing = tuple(
        name
        for name, value in (("retry_rate", retry_rate), ("error_rate", error_rate), ("dlq_growth", dlq_growth))
        if value is None
    )
    return FailureCandidate(
        hashlib.sha256(raw.encode()).hexdigest(),
        "poison_message_candidate",
        tenant_id,
        environment,
        resource_type,
        resource_id,
        partition,
        subject,
        observed_at,
        observed_at,
        retry_rate,
        error_rate,
        dlq_growth,
        "stalled" if offset_stalled else "progressing",
        safe_error_fingerprint(classifications),
        overlay_references,
        min(0.95, 0.35 + 0.12 * len(reasons)),
        min(1.0, len(reasons) / 5),
        reasons,
        missing,
        evidence_references,
    )
