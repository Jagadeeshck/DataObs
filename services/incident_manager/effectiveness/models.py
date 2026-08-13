from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

EFFECTIVENESS_DEFINITION_VERSION = "remediation-effectiveness/1.0.0"


class InterventionType(StrEnum):
    SAFE_REMEDIATION_ACTION = "safe_remediation_action"
    ELASTIC_WORKFLOW = "elastic_workflow"
    MANUAL_TYPED_INTERVENTION = "manual_typed_intervention"


class ProviderStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    CANCELLED = "cancelled"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    CONTRADICTED = "contradicted"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class EffectivenessClass(StrEnum):
    VERIFIED_EFFECTIVE = "verified_effective"
    INCONCLUSIVE = "inconclusive"
    NO_OBSERVED_EFFECT = "no_observed_effect"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"
    CONTRADICTED = "contradicted"


class EvidenceCoverage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    execution_evidence: bool
    provider_evidence: bool
    verification_evidence: bool
    recovery_evidence: bool
    stability_evidence: bool
    recurrence_evidence: bool

    @property
    def coverage(self) -> float:
        return sum(self.model_dump().values()) / 6


def episode_identity(
    tenant_id: str, environment: str, incident_id: str, execution_id: str, definition_version: str
) -> str:
    value = "\x1f".join((tenant_id, environment, incident_id, execution_id, definition_version))
    return "remediation-episode-" + hashlib.sha256(value.encode()).hexdigest()


class RemediationEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    episode_id: str
    tenant_id: str
    environment: str
    incident_id: str
    intervention_type: InterventionType
    intervention_id: str
    execution_id: str
    action_catalog_id: str | None = None
    action_catalog_version: str | None = None
    workflow_id: str | None = None
    workflow_version: str | None = None
    provider_status: ProviderStatus
    verification_status: VerificationStatus
    effectiveness_class: EffectivenessClass
    evidence: EvidenceCoverage
    evidence_coverage: float = Field(ge=0, le=1)
    execution_started_at: datetime | None = None
    execution_completed_at: datetime | None = None
    verified_effect_at: datetime | None = None
    recovery_observed_at: datetime | None = None
    resolved_at: datetime | None = None
    time_to_verified_effect_ms: int | None = Field(default=None, ge=0)
    recovery_after_action_ms: int | None = Field(default=None, ge=0)
    resolution_after_action_ms: int | None = Field(default=None, ge=0)
    incident_reopened_after: bool = False
    recurrence_observed: bool = False
    actions_after_episode_before_recovery: int = Field(default=0, ge=0)
    recovery_association_observed: bool = False
    attribution_ambiguous: bool = False
    evidence_refs: tuple[str, ...] = Field(default=(), max_length=50)
    source_incident_revision: str
    source_execution_revision: str
    verification_checkpoint: str | None = None
    timeline_checkpoint: str | None = None
    effectiveness_definition_version: str = EFFECTIVENESS_DEFINITION_VERSION
    computed_at: datetime

    @model_validator(mode="after")
    def validate_derived_fields(self):
        # Keep persisted projections honest when they are replayed/deserialized.
        from .classifier import classify

        expected_class = classify(self.provider_status, self.verification_status)
        if self.effectiveness_class != expected_class:
            raise ValueError("effectiveness_class contradicts provider/verification statuses")
        if abs(self.evidence_coverage - self.evidence.coverage) > 1e-9:
            raise ValueError("evidence_coverage must be derived from evidence.coverage")
        if (
            self.effectiveness_class != EffectivenessClass.VERIFIED_EFFECTIVE
            and self.time_to_verified_effect_ms is not None
        ):
            raise ValueError("time_to_verified_effect_ms requires a currently verified-effective episode")
        return self
