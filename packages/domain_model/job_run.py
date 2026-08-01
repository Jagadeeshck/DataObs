"""Canonical, source-neutral job and run contracts.

Platform details live in optional facets; raw SQL, rows, payloads and credentials are
intentionally absent from these contracts.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from .base import DomainModel


class RunState(str, Enum):
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ABORTED = "aborted"
    SKIPPED = "skipped"
    UPSTREAM_FAILED = "upstream_failed"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"
    MISSING = "missing"
    UNKNOWN = "unknown"


class FailureCategory(str, Enum):
    APPLICATION_ERROR = "application_error"
    DATA_QUALITY_FAILURE = "data_quality_failure"
    SOURCE_UNAVAILABLE = "source_unavailable"
    PERMISSION_DENIED = "permission_denied"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    TIMEOUT = "timeout"
    OUT_OF_MEMORY = "out_of_memory"
    EXECUTOR_LOST = "executor_lost"
    FETCH_FAILURE = "fetch_failure"
    SHUFFLE_FAILURE = "shuffle_failure"
    SERIALIZATION_ERROR = "serialization_error"
    SCHEMA_ERROR = "schema_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Facet(DomainModel):
    source_native_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class AirflowDagFacet(Facet):
    dag_id: str
    schedule: Optional[str] = None


class AirflowTaskFacet(Facet):
    task_id: str
    operator: Optional[str] = None
    try_number: int = 1
    map_index: Optional[int] = None


class DbtInvocationFacet(Facet):
    invocation_id: str
    project: Optional[str] = None
    target: Optional[str] = None


class DbtNodeFacet(Facet):
    unique_id: str
    resource_type: Optional[str] = None
    compiled_code_fingerprint: Optional[str] = None


class DbtTestFacet(Facet):
    unique_id: str
    outcome: Optional[str] = None


class SparkApplicationFacet(Facet):
    application_id: str


class SparkJobFacet(Facet):
    spark_job_id: str


class SparkStageFacet(Facet):
    stage_id: str
    attempt: int = 0


class SparkExecutorFacet(Facet):
    executor_id: str
    lost: bool = False


class SparkStreamingFacet(Facet):
    query_id: str
    batch_id: Optional[int] = None
    offset_fingerprint: Optional[str] = None


class Scoped(DomainModel):
    tenant_id: str
    environment: str


class JobOwner(DomainModel):
    team: Optional[str] = None
    contacts: List[str] = Field(default_factory=list)


class JobCodeVersion(DomainModel):
    git_sha: Optional[str] = None
    fingerprint: Optional[str] = None


class JobDeployment(DomainModel):
    version: Optional[str] = None
    deployed_at: Optional[datetime] = None


class JobSchedule(DomainModel):
    kind: Literal["interval", "cron", "external", "event_driven", "ad_hoc", "unknown"] = "unknown"
    expression: Optional[str] = None
    next_expected_at: Optional[datetime] = None
    confidence: float = 0


class JobSLO(DomainModel):
    deadline_seconds: Optional[int] = None
    maximum_duration_ms: Optional[int] = None


class JobHealth(DomainModel):
    state: RunState = RunState.UNKNOWN
    reasons: List[str] = Field(default_factory=list)
    confidence: float = 0


class JobReliability(DomainModel):
    score: Optional[float] = None
    components: Dict[str, Optional[float]] = Field(default_factory=dict)
    formula: str = "weighted available components"
    missing_components: List[str] = Field(default_factory=list)
    confidence: float = 0


class ScheduleSource(str, Enum):
    CONFIGURED = "configured"
    AIRFLOW = "airflow"
    DBT = "dbt"
    OPENLINEAGE = "openlineage"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class ExpectedRunState(str, Enum):
    EXPECTED = "expected"
    ON_TIME = "on_time"
    LATE = "late"
    MISSING = "missing"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED_BY_POLICY = "skipped_by_policy"
    EXCLUDED_BY_MAINTENANCE = "excluded_by_maintenance"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


class ReliabilityState(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    BREACHING = "breaching"
    RECOVERING = "recovering"
    NO_DATA = "no_data"
    STALE = "stale"
    DISABLED = "disabled"
    ERROR = "error"
    UNKNOWN = "unknown"


class MaintenanceWindow(DomainModel):
    starts_at: datetime
    ends_at: datetime
    reason: Optional[str] = None


class ReliabilityPolicy(Scoped):
    job_id: str
    enabled: bool = True
    schedule_source: ScheduleSource = ScheduleSource.UNKNOWN
    timezone: str = "UTC"
    expected_schedule: Optional[JobSchedule] = None
    allowed_start_delay_seconds: int = 0
    completion_deadline_seconds: Optional[int] = None
    maximum_duration_ms: Optional[int] = None
    missing_run_grace_seconds: int = 0
    minimum_success_rate: float = 0.95
    maximum_retry_rate: float = 0.05
    maximum_missing_run_rate: float = 0.0
    maximum_quality_failure_rate: float = 0.0
    maximum_dependency_failure_rate: float = 0.0
    evaluation_windows_seconds: List[int] = Field(default_factory=lambda: [86400])
    minimum_sample_size: int = 1
    minimum_available_components: int = 1
    component_weights: Dict[str, float] = Field(default_factory=dict)
    maintenance_windows: List[MaintenanceWindow] = Field(default_factory=list)
    business_calendar_exclusions: List[str] = Field(default_factory=list)
    owner: Optional[JobOwner] = None
    revision: int = 1
    etag: str
    created_at: datetime
    updated_at: datetime


class ExpectedRun(Scoped):
    expected_run_id: str
    job_id: str
    scheduled_at: datetime
    permitted_start_at: datetime
    permitted_start_until: datetime
    deadline_at: Optional[datetime] = None
    schedule_source: ScheduleSource
    schedule_confidence: float = 0
    actual_run_id: Optional[str] = None
    status: ExpectedRunState = ExpectedRunState.EXPECTED
    reason_codes: List[str] = Field(default_factory=list)
    maintenance_exclusion: Optional[str] = None
    evaluated_at: datetime


class RunReliabilityEvaluation(Scoped):
    evaluation_id: str
    job_id: str
    run_id: str
    expected_run_id: Optional[str] = None
    run_state: RunState
    start_delay_result: Optional[bool] = None
    deadline_result: Optional[bool] = None
    duration_result: Optional[bool] = None
    retry_result: Optional[bool] = None
    quality_result: Optional[bool] = None
    dependency_result: Optional[bool] = None
    failure_category: Optional[FailureCategory] = None
    confidence: float = 0
    evidence_coverage: float = 0
    missing_inputs: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    evidence_references: List[str] = Field(default_factory=list)
    evaluated_at: datetime
    policy_revision: int
    schema_version: str = "v1"


class JobReliabilitySnapshot(Scoped):
    job_id: str
    state: ReliabilityState
    score: Optional[float] = None
    components: Dict[str, Optional[float]] = Field(default_factory=dict)
    normalized_weights: Dict[str, float] = Field(default_factory=dict)
    sample_counts: Dict[str, int] = Field(default_factory=dict)
    evaluated_from: datetime
    evaluated_until: datetime
    expected_run_count: int = 0
    observed_run_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    late_count: int = 0
    missing_count: int = 0
    retry_count: int = 0
    duration_breach_count: int = 0
    quality_failure_count: int = 0
    dependency_failure_count: int = 0
    confidence: float = 0
    missing_components: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    current_streaks: Dict[str, int] = Field(default_factory=dict)
    previous_period_comparison: Optional[Dict[str, float]] = None
    policy_revision: int
    observed_at: datetime


class JobDefinition(Scoped):
    job_id: str
    qualified_name: str
    platform: Literal["airflow", "dbt", "spark", "openlineage"]
    namespace: str
    name: str
    owner: Optional[JobOwner] = None
    schedule: Optional[JobSchedule] = None


class RunFailure(DomainModel):
    category: FailureCategory = FailureCategory.UNKNOWN
    redacted_summary: str
    fingerprint: str
    source_category: Optional[str] = None
    stack_trace_reference: Optional[str] = None
    safe_evidence_reference: Optional[str] = None
    confidence: float = 0


class RunDatasetIO(DomainModel):
    asset_id: str
    direction: Literal["input", "output"]
    records: Optional[int] = None
    bytes: Optional[int] = None


class RunMetric(DomainModel):
    name: str
    value: float
    unit: str


class RunResourceUsage(DomainModel):
    cpu_ms: Optional[int] = None
    memory_byte_ms: Optional[int] = None
    gc_ms: Optional[int] = None
    shuffle_bytes: Optional[int] = None
    spill_bytes: Optional[int] = None


class RunCostSummary(DomainModel):
    status: Literal["complete", "partial", "not_configured", "unknown"] = "not_configured"
    amount: Optional[float] = None
    currency: Optional[str] = None
    formula: Optional[str] = None
    confidence: float = 0
    missing_inputs: List[str] = Field(default_factory=list)


class RunChange(DomainModel):
    kind: str
    reference: str
    observed_at: datetime


class RunEvidence(DomainModel):
    kind: str
    reference: str
    summary: str


class JobRun(Scoped):
    run_id: str
    job_id: str
    source_run_id: str
    platform: Literal["airflow", "dbt", "spark", "openlineage"]
    state: RunState = RunState.UNKNOWN
    source_state: Optional[str] = None
    parent_run_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    attempt_count: int = 1
    inputs: List[RunDatasetIO] = Field(default_factory=list)
    outputs: List[RunDatasetIO] = Field(default_factory=list)
    resource_usage: Optional[RunResourceUsage] = None
    trace_id: Optional[str] = None
    logs_reference: Optional[str] = None
    code_version: Optional[JobCodeVersion] = None
    deployment_version: Optional[JobDeployment] = None
    evidence_coverage: List[str] = Field(default_factory=list)
    failure: Optional[RunFailure] = None
    airflow: Optional[AirflowDagFacet] = None
    dbt: Optional[DbtInvocationFacet] = None
    spark: Optional[SparkApplicationFacet] = None
    unknown_facets: Dict[str, Any] = Field(default_factory=dict)


class JobRunAttempt(Scoped):
    attempt_id: str
    run_id: str
    number: int
    state: RunState
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    failure: Optional[RunFailure] = None
    retry_reason: Optional[str] = None


class TaskDefinition(DomainModel):
    task_id: str
    job_id: str
    name: str
    dependencies: List[str] = Field(default_factory=list)


class TaskRun(Scoped):
    task_id: str
    run_id: str
    state: RunState
    source_state: Optional[str] = None
    duration_ms: Optional[int] = None
    attempt: int = 1
    upstream_tasks: List[str] = Field(default_factory=list)
    failure: Optional[RunFailure] = None
    airflow: Optional[AirflowTaskFacet] = None
    dbt: Optional[DbtNodeFacet] = None


class StageTaskSummary(DomainModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    sampled: int = 0
    complete: bool = False


class StageRun(Scoped):
    stage_id: str
    run_id: str
    attempt: int = 0
    state: RunState
    duration_ms: Optional[int] = None
    tasks: StageTaskSummary = Field(default_factory=StageTaskSummary)
    shuffle_read_bytes: Optional[int] = None
    shuffle_write_bytes: Optional[int] = None
    spill_bytes: Optional[int] = None
    failure: Optional[RunFailure] = None
    spark: Optional[SparkStageFacet] = None


class StreamingQueryRun(Scoped):
    query_id: str
    run_id: str
    state: RunState
    batch_id: Optional[int] = None
    input_rows: Optional[int] = None
    input_rows_per_second: Optional[float] = None
    processed_rows_per_second: Optional[float] = None
    batch_duration_ms: Optional[int] = None
    spark: Optional[SparkStreamingFacet] = None


class CriticalPathSegment(DomainModel):
    entity_id: str
    duration_ms: int
    waiting_ms: int = 0
    execution_ms: int = 0
    slack_ms: Optional[int] = None
    blocking_dependencies: List[str] = Field(default_factory=list)


class CriticalPath(DomainModel):
    segments: List[CriticalPathSegment]
    confidence: float
    incomplete_graph: bool = False


class RunComparison(DomainModel):
    base_run_id: str
    target_run_id: str
    mode: str
    deltas: Dict[str, Optional[float]]
    new_entities: List[str] = Field(default_factory=list)
    removed_entities: List[str] = Field(default_factory=list)
    confidence: float = 0
    missing_evidence: List[str] = Field(default_factory=list)


class RunActionEligibility(DomainModel):
    eligible: bool
    actions: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    approval_required: bool = True


class RunActionRequest(DomainModel):
    request_id: str
    run_id: str
    action: str
    reason: str
    parameters: Dict[str, str] = Field(default_factory=dict)
    idempotency_key: str


class RunActionResult(DomainModel):
    request_id: str
    state: Literal["pending_approval", "approved", "executing", "succeeded", "failed", "denied"]
    source_reference: Optional[str] = None
    verified_run_id: Optional[str] = None
