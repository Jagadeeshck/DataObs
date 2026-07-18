from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from .base import ProductEntity


class FindingType(StrEnum):
    SCHEMA_CHANGE = "schema_change"
    FRESHNESS_BREACH = "freshness_breach"
    DATA_QUALITY_FAILURE = "data_quality_failure"
    SCANNER_FAILURE = "scanner_failure"
    SOURCE_UNAVAILABLE = "source_unavailable"
    PROFILE_ANOMALY = "profile_anomaly"
    LINEAGE_IMPACT_WARNING = "lineage_impact_warning"


class SignalType(StrEnum):
    POSTGRES_SCHEMA_CHANGE = "postgres_schema_change"
    FRESHNESS_MEASUREMENT = "freshness_measurement"
    QUALITY_RESULT = "quality_result"
    SCANNER_ERROR = "scanner_error"
    SOURCE_CONNECTION_FAILURE = "source_connection_failure"
    OPENLINEAGE_RUN_FAILURE = "openlineage_run_failure"
    MONITOR_ANOMALY = "monitor_anomaly"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    ACTIVE = "active"
    RECOVERED = "recovered"
    SUPPRESSED = "suppressed"


class IncidentState(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    CLOSED = "closed"


def deterministic_id(prefix: str, parts: list[str]) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


class EvidenceReference(ProductEntity):
    id: str = Field(default="evidence")
    evidence_type: str
    reference_id: str
    index: str | None = None
    url: str | None = None
    summary: str | None = None


class Finding(ProductEntity):
    id: str = ""
    finding_type: FindingType
    signal_type: SignalType
    source_event_id: str
    source_event_version: str = "v1"
    asset_id: str
    scanner_id: str | None = None
    monitor_id: str | None = None
    policy_id: str | None = None
    title: str
    summary: str
    observed_value: dict[str, Any] = Field(default_factory=dict)
    expected_value: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    downstream_impact: list[str] = Field(default_factory=list)
    downstream_asset_count: int = 0
    trace_id: str | None = None
    span_id: str | None = None
    request_id: str | None = None
    first_observed_at: datetime
    last_observed_at: datetime
    recovery_signal: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def _blank_ok(cls, value: str | None) -> str:
        return value or ""

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            self.id = deterministic_id(
                "finding",
                [
                    self.tenant_id,
                    self.environment,
                    self.asset_id,
                    str(self.finding_type),
                    str(self.signal_type),
                    self.source_event_id,
                    self.source_event_version,
                ],
            )


class Incident(ProductEntity):
    incident_state: IncidentState = IncidentState.OPEN
    severity: Severity = Severity.MEDIUM
    deduplication_key: str
    correlation_key: str | None = None
    finding_ids: list[str] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    root_cause_candidates: list[dict[str, Any]] = Field(default_factory=list)
    impact_summary: str | None = None
    technical_score: float = 0.0
    business_impact_score: float = 0.0
    severity_factors: dict[str, Any] = Field(default_factory=dict)
    occurrence_count: int = 1
    most_recent_evidence: list[dict[str, Any]] = Field(default_factory=list)
    workflow_ref: str | None = None
    workflow_execution_id: str | None = None
    elastic_case_id: str | None = None
    elastic_case_version: str | None = None
    external_incident_id: str | None = None
    notification_state: str = "pending"
    opened_at: datetime | None = None
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    resolution_reason: str | None = None
    recovery_evidence: list[dict[str, Any]] = Field(default_factory=list)
    seq_no: int | None = None
    primary_term: int | None = None
