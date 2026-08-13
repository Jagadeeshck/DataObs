from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SimilarityClassification(StrEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FeatureMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str
    weight: float
    match: str
    similarity: float = Field(ge=0, le=1)


class IncidentSimilarity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_incident_id: str
    candidate_incident_id: str
    similarity_score: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    classification: SimilarityClassification
    feature_version: str
    scoring_version: str
    matched_features: list[FeatureMatch]
    different_features: list[FeatureMatch]
    unavailable_features: list[str]
    reason_codes: list[str]
    computed_at: datetime
    source_revision: str
    candidate_revision: str
    same_structural_signature: bool


class RecurrenceType(StrEnum):
    SAME_FAILURE_SIGNATURE = "same_failure_signature"
    SAME_ASSET_FAILURE = "same_asset_failure"
    SAME_RULE_FAILURE = "same_rule_failure"
    SAME_DATA_PRODUCT_FAILURE = "same_data_product_failure"
    SAME_BUSINESS_SERVICE_FAILURE = "same_business_service_failure"
    SAME_ROOT_CAUSE_CATEGORY = "same_root_cause_category"
    MANUAL_CONFIRMED_RECURRENCE = "manual_confirmed_recurrence"


class RelationshipStatus(StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
