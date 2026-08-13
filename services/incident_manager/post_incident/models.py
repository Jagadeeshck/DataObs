from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.incident_manager.automation.safe_text import validate_safe_text

MAX_EVIDENCE_REFS = 50


class RequirementState(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    WAIVED = "waived"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"


class RootCauseClassification(StrEnum):
    UNKNOWN = "unknown"
    HYPOTHESIS = "hypothesis"
    PROBABLE = "probable"
    CONFIRMED = "confirmed"


class FollowUpStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_type: str = Field(
        pattern=r"^(finding|incident_event|workflow_execution|verification|case|pathway|lineage|monitor|job_run)$"
    )
    reference_id: str = Field(min_length=1, max_length=200)


class RootCauseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classification: RootCauseClassification
    summary: str = Field(max_length=2000)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=MAX_EVIDENCE_REFS)
    confidence: float | None = Field(default=None, ge=0, le=1)
    author: str | None = Field(default=None, max_length=200)
    created_at: datetime

    @field_validator("summary")
    @classmethod
    def safe_summary(cls, value: str) -> str:
        return validate_safe_text(value, field="root cause summary", maximum=2000)

    @field_validator("author")
    @classmethod
    def confirmed_has_actor(cls, value: str | None, info: Any) -> str | None:
        if info.data.get("classification") == RootCauseClassification.CONFIRMED and not value:
            raise ValueError("confirmed root cause requires an authenticated actor")
        return value


class ReviewSections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(default="", max_length=4000)
    technical_impact: str = Field(default="", max_length=4000)
    business_impact: str = Field(default="", max_length=4000)
    mitigation: str = Field(default="", max_length=4000)
    recovery: str = Field(default="", max_length=4000)
    went_well: list[str] = Field(default_factory=list, max_length=20)
    could_be_improved: list[str] = Field(default_factory=list, max_length=20)
    lessons: list[str] = Field(default_factory=list, max_length=20)
    preventive_measures: list[str] = Field(default_factory=list, max_length=20)
    root_causes: list[RootCauseEntry] = Field(default_factory=list, max_length=20)

    @field_validator("summary", "technical_impact", "business_impact", "mitigation", "recovery")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return validate_safe_text(value, field="review text", maximum=4000, allow_empty=True)

    @field_validator("went_well", "could_be_improved", "lessons", "preventive_measures")
    @classmethod
    def safe_list(cls, values: list[str]) -> list[str]:
        return [validate_safe_text(value, field="lesson", maximum=1000) for value in values]


class PolicyDecision(BaseModel):
    policy_id: str
    policy_version: str
    policy_hash: str
    decision: RequirementState
    decision_reason: str


class IncidentReview(BaseModel):
    review_id: str
    tenant_id: str
    environment: str
    incident_id: str
    review_generation: int = Field(ge=1)
    supersedes: str | None = None
    status: ReviewStatus = ReviewStatus.DRAFT
    requirement: PolicyDecision
    owner: str
    reviewers: list[str] = Field(default_factory=list, max_length=20)
    due_at: datetime | None = None
    completed_at: datetime | None = None
    incident_revision: str
    evidence_cutoff: datetime
    timeline_cutoff: str | None = None
    source_changed: bool = False
    sections: ReviewSections
    timeline_event_ids: list[str] = Field(default_factory=list, max_length=200)
    important_event_ids: list[str] = Field(default_factory=list, max_length=100)
    created_at: datetime
    updated_at: datetime
    revision: int = 1


def review_identity(tenant: str, environment: str, incident_id: str, generation: int) -> str:
    raw = json.dumps([tenant, environment, incident_id, generation], separators=(",", ":"))
    return "incident-review-" + hashlib.sha256(raw.encode()).hexdigest()[:24]
