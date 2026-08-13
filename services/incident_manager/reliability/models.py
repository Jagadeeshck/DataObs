from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.domain_model.slo import BurnSignal, ErrorBudget

FORMULA_VERSION = "incident-response-objective/1.0.0"
POLICY_VERSION = "incident-response-policy/1.0.0"
APPROACHING_BREACH_RATIO = 0.8


class ResponseMetricType(StrEnum):
    TIME_TO_ACKNOWLEDGE = "time_to_acknowledge"
    TIME_TO_INVESTIGATION = "time_to_investigation"
    TIME_TO_MITIGATION = "time_to_mitigation"
    TIME_TO_RECOVERY = "time_to_recovery"
    TIME_TO_RESOLUTION = "time_to_resolution"


class ObjectiveResultState(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    WITHIN_TARGET = "within_target"
    APPROACHING_BREACH = "approaching_breach"
    BREACHED = "breached"
    MET = "met"
    MET_AFTER_BREACH = "met_after_breach"
    UNAVAILABLE = "unavailable"
    EXCLUDED = "excluded"


class IncidentResponseObjectiveDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    tenant_id: str
    environment: str
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    metric_type: ResponseMetricType
    severity_selector: tuple[str, ...] = ()
    priority_selector: tuple[str, ...] = ()
    target_duration_seconds: int = Field(gt=0, le=31_536_000)
    objective: float = Field(gt=0, le=1)
    evaluation_window: str
    window_type: str = "rolling"
    missing_evidence_policy: str = "unknown"
    state: str = "draft"
    policy_version: str = POLICY_VERSION
    definition_revision: int = Field(default=1, ge=1)
    created_by: str
    created_at: datetime
    updated_at: datetime


class IncidentResponseObjectiveAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    incident_id: str
    objective_definition_id: str
    definition_revision: int
    metric_type: ResponseMetricType
    objective: float = Field(gt=0, le=1)
    target_duration_seconds: int = Field(gt=0)
    effective_at: datetime
    deadline_at: datetime
    source_incident_revision: str
    policy_version: str
    policy_snapshot_hash: str

    @model_validator(mode="after")
    def deadline_is_derived(self):
        if self.deadline_at != self.effective_at + timedelta(seconds=self.target_duration_seconds):
            raise ValueError("deadline_at must be derived from effective_at and target duration")
        return self

    @classmethod
    def snapshot(
        cls,
        definition: IncidentResponseObjectiveDefinition,
        *,
        incident_id: str,
        effective_at: datetime,
        source_incident_revision: str,
    ):
        payload = {
            "definition_id": definition.id,
            "revision": definition.definition_revision,
            "metric_type": definition.metric_type.value,
            "objective": definition.objective,
            "target_duration_seconds": definition.target_duration_seconds,
            "policy_version": definition.policy_version,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(
            incident_id=incident_id,
            objective_definition_id=definition.id,
            definition_revision=definition.definition_revision,
            metric_type=definition.metric_type,
            objective=definition.objective,
            target_duration_seconds=definition.target_duration_seconds,
            effective_at=effective_at,
            deadline_at=effective_at + timedelta(seconds=definition.target_duration_seconds),
            source_incident_revision=source_incident_revision,
            policy_version=definition.policy_version,
            policy_snapshot_hash=digest,
        )


class IncidentObjectiveResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    incident_id: str
    definition_id: str
    metric_type: ResponseMetricType
    state: ObjectiveResultState
    target_duration_seconds: int
    actual_duration_seconds: float | None = None
    historical_breach: bool = False
    evidence_status: str
    coverage: float = Field(ge=0, le=1)
    reason_codes: tuple[str, ...] = ()


class IncidentResponseObjectiveEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    definition_id: str
    definition_revision: int
    tenant_id: str
    environment: str
    window_start: datetime
    window_end: datetime
    eligible_count: int
    met_count: int
    breached_count: int
    unknown_count: int
    excluded_count: int
    coverage_ratio: float
    actual_compliance: float | None
    objective: float
    error_budget: ErrorBudget
    burn: BurnSignal
    state: str
    formula_version: str = FORMULA_VERSION
    evaluated_at: datetime
