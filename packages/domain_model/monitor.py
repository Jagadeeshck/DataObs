from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import Field, model_validator

from .base import DomainModel, ProductEntity, utc_now


class MonitorType(str, Enum):
    FRESHNESS = "freshness"
    VOLUME = "volume"
    SCHEMA_CHANGE = "schema_change"
    FIELD_NULL_RATE = "field_null_rate"
    FIELD_UNIQUE_RATE = "field_unique_rate"
    FIELD_ZERO_RATE = "field_zero_rate"
    FIELD_NEGATIVE_RATE = "field_negative_rate"
    FIELD_CARDINALITY = "field_cardinality"
    FIELD_DISTRIBUTION = "field_distribution"
    FIELD_RANGE = "field_range"
    METRIC = "metric"
    METRIC_COMPARISON = "metric_comparison"
    VALIDATION = "validation"
    CUSTOM_SQL_AGGREGATE = "custom_sql_aggregate"
    QUERY_PERFORMANCE = "query_performance"
    PIPELINE_DURATION = "pipeline_duration"
    PIPELINE_MISSING_RUN = "pipeline_missing_run"
    PATHWAY_LATENCY = "pathway_latency"
    CONSUMER_LAG = "consumer_lag"
    RETENTION_RISK = "retention_risk"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    DLQ_RATE = "dlq_rate"
    SOURCE_AVAILABILITY = "source_availability"
    COLLECTOR_HEALTH = "collector_health"


class ThresholdMode(str, Enum):
    FIXED = "fixed"
    LEARNED = "learned"
    HYBRID = "hybrid"
    RELATIVE_CHANGE = "relative_change"
    RANGE = "range"
    RATE_OF_CHANGE = "rate_of_change"
    MISSING_EVENT = "missing_event"


class BaselineMode(str, Enum):
    STATIC = "static"
    ADAPTIVE = "adaptive"
    HYBRID = "hybrid"


class BaselineState(str, Enum):
    COLLECTING = "collecting"
    READY = "ready"
    STALE = "stale"
    DEGRADED = "degraded"
    RESETTING = "resetting"
    DISABLED = "disabled"
    ERROR = "error"


class MonitorState(str, Enum):
    DRAFT = "draft"
    RECOMMENDED = "recommended"
    ENABLED = "enabled"
    DISABLED = "disabled"
    LEARNING = "learning"
    ACTIVE = "active"
    DEGRADED = "degraded"
    SUPPRESSED = "suppressed"
    ARCHIVED = "archived"
    ERROR = "error"


class ColdStartState(str, Enum):
    COLLECTING = "collecting"
    PROVISIONAL = "provisional"
    MATURE = "mature"
    RESET_REQUIRED = "reset_required"
    STALE = "stale"


class MonitorTarget(DomainModel):
    asset_id: str | None = None
    field_id: str | None = None
    pathway_id: str | None = None
    pipeline_id: str | None = None
    service_id: str | None = None
    source_type: Literal["postgresql", "deterministic_test"] = "postgresql"
    connection_ref: str | None = None
    schema_name: str | None = None
    table_name: str | None = None
    columns: List[str] = Field(default_factory=list)
    timestamp_column: str | None = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MonitorSelector(DomainModel):
    asset_ids: List[str] = Field(default_factory=list)
    field_ids: List[str] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)


class MonitorSchedule(DomainModel):
    interval: str = "5m"
    timezone: str = "UTC"
    maintenance_windows: List[str] = Field(default_factory=list)
    business_calendar_exclusions: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_interval(self):
        import re

        match = re.fullmatch(r"([1-9][0-9]*)(m|h|d)", self.interval)
        if not match:
            raise ValueError("schedule interval must use a bounded m, h, or d duration")
        seconds = int(match.group(1)) * {"m": 60, "h": 3600, "d": 86400}[match.group(2)]
        if seconds < 60 or seconds > 31 * 86400:
            raise ValueError("schedule interval must be between 1m and 31d")
        return self


class MonitorThresholdPolicy(DomainModel):
    mode: ThresholdMode
    minimum: float | None = None
    maximum: float | None = None
    relative_change: float | None = None
    fixed_safety_minimum: float | None = None
    fixed_safety_maximum: float | None = None


class BaselineTrainingWindow(DomainModel):
    observations: int = Field(default=60, ge=3, le=10000)
    minimum_samples: int = Field(default=14, ge=3, le=10000)
    maximum_age: str = "90d"


class BaselineUpdatePolicy(DomainModel):
    learning_delay: int = Field(default=2, ge=0, le=100)
    exclude_breaches: bool = True
    exclude_suppressed: bool = False
    exclude_backfills: bool = True
    exclude_maintenance: bool = True
    exclude_stale: bool = True
    exclude_incomplete: bool = True


class BaselineDriftPolicy(DomainModel):
    enabled: bool = True
    regime_change_evaluations: int = Field(default=5, ge=3, le=100)


class MonitorBaselinePolicy(DomainModel):
    enabled: bool = True
    mode: BaselineMode = BaselineMode.ADAPTIVE
    method: Literal["rolling_median", "mad", "quantile", "robust_quantiles", "iqr", "ewma", "same_period"] = "mad"
    history_points: int = Field(default=168, ge=3, le=10000)
    minimum_samples: int = Field(default=12, ge=3)
    sensitivity: Literal["low", "medium", "high"] = "medium"
    training_window: BaselineTrainingWindow | None = None
    seasonality: List[Literal["hour_of_day", "day_of_week", "weekday_weekend", "weekly", "custom"]] = Field(
        default_factory=list, max_length=2
    )
    update_policy: BaselineUpdatePolicy = Field(default_factory=BaselineUpdatePolicy)
    drift: BaselineDriftPolicy = Field(default_factory=BaselineDriftPolicy)
    stale_after: str = "48h"
    timezone: str = "UTC"

    @model_validator(mode="after")
    def normalize_window(self):
        if self.training_window is not None:
            self.history_points = self.training_window.observations
            self.minimum_samples = self.training_window.minimum_samples
        if self.minimum_samples > self.history_points:
            raise ValueError("minimum_samples cannot exceed the observation window")
        return self


class MonitorAlertPolicy(DomainModel):
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    consecutive_breaches: int = Field(default=1, ge=1)
    rca_auto_trigger: bool = False


class MonitorNotificationPolicyRef(DomainModel):
    policy_id: str


class MonitorWorkflowPolicyRef(DomainModel):
    policy_id: str
    requires_approval: bool = True


class MonitorDefinition(ProductEntity):
    monitor_type: MonitorType
    target: MonitorTarget
    selector: MonitorSelector = Field(default_factory=MonitorSelector)
    schedule: MonitorSchedule = Field(default_factory=MonitorSchedule)
    threshold: MonitorThresholdPolicy
    baseline: MonitorBaselinePolicy | None = None
    alert: MonitorAlertPolicy = Field(default_factory=MonitorAlertPolicy)
    notification_policy_ref: MonitorNotificationPolicyRef | None = None
    workflow_policy_ref: MonitorWorkflowPolicyRef | None = None
    monitor_version: int = Field(default=1, ge=1)
    revision: int = Field(default=1, ge=1)
    creation_source: Literal["UI", "API", "YAML", "recommendation", "import"] = "API"
    managed_by: str
    etag: str
    last_applied_checksum: str | None = None
    state: MonitorState = MonitorState.DRAFT


class MonitorObservation(DomainModel):
    execution_id: str = "legacy"
    monitor_id: str
    tenant_id: str
    environment: str
    observed_at: datetime = Field(default_factory=utc_now)
    value: float | None = None
    sample_count: int = 0
    missing_data: bool = False
    dimensions: Dict[str, str] = Field(default_factory=dict)
    definition_revision: int = 1
    unit: str = "count"
    provider: str = "unknown"
    source_evidence_refs: List[str] = Field(default_factory=list)
    collection_duration_ms: int = Field(default=0, ge=0)
    trace_id: str | None = None
    schema_version: str = "v1"


class MonitorEvaluation(DomainModel):
    evaluation_id: str
    monitor_id: str
    tenant_id: str
    environment: str
    definition_revision: int
    baseline_version: str | None = None
    evaluated_at: datetime = Field(default_factory=utc_now)
    observation: MonitorObservation
    expected_minimum: float | None = None
    expected_maximum: float | None = None
    method: str
    baseline_window: str | None = None
    seasonal_cohort: str | None = None
    seasonal_cohort_reason: str | None = None
    sensitivity: str
    threshold_calculation: str
    sample_count: int
    confidence: float = Field(ge=0, le=1)
    cold_start_state: ColdStartState
    missing_inputs: List[str] = Field(default_factory=list)
    exclusion_reasons: List[str] = Field(default_factory=list)
    comparison_periods: List[str] = Field(default_factory=list)
    anomaly_score: float | None = None
    breached: bool = False


class MonitorFinding(DomainModel):
    finding_id: str
    monitor_id: str
    evaluation_id: str
    tenant_id: str
    environment: str
    state: Literal["open", "recovered", "suppressed"]
    severity: Literal["low", "medium", "high", "critical"]
    deduplication_key: str
    definition_revision: int
    baseline_version: str | None = None
    incident_id: str | None = None
    product_ids: List[str] = Field(default_factory=list)


class MonitorRecommendation(DomainModel):
    id: str
    tenant_id: str
    monitor_type: MonitorType
    target: MonitorTarget
    rationale: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    expected_compute_cost: str
    expected_collection_permissions: List[str] = Field(default_factory=list)
    proposed_baseline: MonitorBaselinePolicy | None = None
    proposed_fixed_safety_threshold: MonitorThresholdPolicy | None = None
    confidence: float = Field(ge=0, le=1)
    business_priority: str
    duplication_analysis: str
    coverage_gap_closed: List[str] = Field(default_factory=list)
    risk: str
    state: Literal["proposed", "accepted", "rejected", "deferred", "expired", "applied", "superseded"] = "proposed"


class MonitorSuppression(DomainModel):
    id: str
    monitor_id: str
    tenant_id: str
    starts_at: datetime
    ends_at: datetime
    reason: str
    approved_by: str


class MonitorCoverage(DomainModel):
    scope_type: str
    scope_id: str
    state: Literal[
        "covered",
        "partially_covered",
        "recommended",
        "not_covered",
        "not_applicable",
        "not_configured",
        "degraded",
        "unknown",
    ]
    numerator: int
    denominator: int
    exclusions: List[str] = Field(default_factory=list)
    by_category: Dict[str, str] = Field(default_factory=dict)
    high_risk_gaps: List[str] = Field(default_factory=list)
    stale_or_broken_monitors: List[str] = Field(default_factory=list)
    recommendation_count: int = 0


class MonitorTuningAnalysis(DomainModel):
    monitor_id: str
    reasons: List[str] = Field(default_factory=list)
    proposed_patch: Dict[str, Any] = Field(default_factory=dict)
    requires_human_approval: bool = True


class MonitorAuditEvent(DomainModel):
    monitor_id: str
    tenant_id: str
    event_type: str
    actor: str
    occurred_at: datetime = Field(default_factory=utc_now)
    revision: int
    changes: Dict[str, Any] = Field(default_factory=dict)


# Compatibility alias. New code should use MonitorDefinition.
Monitor = MonitorDefinition
