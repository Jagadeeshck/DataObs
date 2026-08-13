from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .features import IncidentFeatures
from .fingerprint import FAILURE_SIGNATURE_VERSION, failure_signature_fingerprint
from .models import IncidentSimilarity, RecurrenceType, RelationshipStatus
from .similarity import MIN_RECURRENCE_CONFIDENCE, MIN_RECURRENCE_FAMILIES, RECURRENCE_CANDIDATE_THRESHOLD


class MembershipType(StrEnum):
    MACHINE_CANDIDATE = "machine_candidate"
    CONFIRMED = "confirmed"
    MANUAL = "manual"


class IncidentRecurrence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationship_id: str
    tenant_id: str
    environment: str
    current_incident_id: str
    prior_incident_id: str
    recurrence_type: RecurrenceType
    status: RelationshipStatus = RelationshipStatus.CANDIDATE
    confidence: float = Field(ge=0, le=1)
    similarity_score: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    reason_codes: list[str]
    signature_version: str
    scoring_version: str
    feature_version: str
    first_seen_at: datetime
    previous_seen_at: datetime
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    actor: str | None = None
    decision_at: datetime | None = None
    decision_reason: str | None = Field(default=None, max_length=500)
    revision: int = 1


class IncidentFamily(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family_id: str
    family_type: RecurrenceType
    tenant_id: str
    environment: str
    first_incident_at: datetime
    latest_incident_at: datetime
    incident_count: int = Field(ge=0)
    representative_signature: str
    affected_assets: list[str] = Field(default_factory=list, max_length=100)
    data_products: list[str] = Field(default_factory=list, max_length=100)
    business_services: list[str] = Field(default_factory=list, max_length=100)
    status: str = "active"


class IncidentFamilyMembership(BaseModel):
    model_config = ConfigDict(extra="forbid")
    membership_id: str
    family_id: str
    incident_id: str
    membership_type: MembershipType
    confidence: float = Field(ge=0, le=1)
    reason_codes: list[str]
    created_at: datetime


def _identity(prefix: str, parts: list[str]) -> str:
    raw = json.dumps(parts, separators=(",", ":"), ensure_ascii=True)
    return prefix + hashlib.sha256(raw.encode()).hexdigest()[:32]


def relationship_identity(tenant: str, environment: str, a: str, b: str, scoring_version: str | None = None) -> str:
    """Identify the logical relationship, independently of scoring generation."""
    first, second = sorted((a, b))
    return _identity("recurrence-", [tenant, environment, "recurrence", first, second])


def family_identity(tenant: str, environment: str, features: IncidentFeatures) -> str:
    signature = failure_signature_fingerprint(features.failure_signature)
    return _identity("incident-family-", [tenant, environment, FAILURE_SIGNATURE_VERSION, signature])


def propose_recurrence(
    source: IncidentFeatures,
    candidate: IncidentFeatures,
    similarity: IncidentSimilarity,
    *,
    source_opened_at: datetime | None,
    candidate_opened_at: datetime | None,
) -> IncidentRecurrence | None:
    if similarity.source_incident_id != source.incident_id or similarity.candidate_incident_id != candidate.incident_id:
        raise ValueError("similarity pair does not match supplied incidents")
    if source.tenant_id != candidate.tenant_id:
        raise ValueError("cross-tenant recurrence is prohibited")
    if source.environment != candidate.environment:
        raise ValueError("cross-environment recurrence is prohibited")
    if (
        similarity.source_revision != source.source_revision
        or similarity.candidate_revision != candidate.source_revision
    ):
        raise ValueError("stale similarity revisions")
    if source.incident_id == candidate.incident_id or source.merged_from or candidate.merged_from:
        return None
    if source.split_from or candidate.split_from or not source_opened_at or not candidate_opened_at:
        return None
    prior, current = (candidate, source) if candidate_opened_at < source_opened_at else (source, candidate)
    previous_at, current_at = sorted((candidate_opened_at, source_opened_at))
    if previous_at == current_at:
        return None
    independent = sum(item.similarity > 0 for item in similarity.matched_features)
    if (
        similarity.similarity_score < RECURRENCE_CANDIDATE_THRESHOLD
        or similarity.confidence < MIN_RECURRENCE_CONFIDENCE
        or independent < MIN_RECURRENCE_FAMILIES
    ):
        return None
    matched = {item.feature for item in similarity.matched_features if item.similarity == 1}
    same_signature = failure_signature_fingerprint(source.failure_signature) == failure_signature_fingerprint(
        candidate.failure_signature
    )
    if same_signature:
        recurrence_type = RecurrenceType.SAME_FAILURE_SIGNATURE
    else:
        supported = (
            ("primary_asset", RecurrenceType.SAME_ASSET_FAILURE),
            ("affected_assets", RecurrenceType.SAME_ASSET_FAILURE),
            ("rule_ids", RecurrenceType.SAME_RULE_FAILURE),
            ("data_product_ids", RecurrenceType.SAME_DATA_PRODUCT_FAILURE),
            ("business_services", RecurrenceType.SAME_BUSINESS_SERVICE_FAILURE),
            ("confirmed_root_cause_categories", RecurrenceType.SAME_ROOT_CAUSE_CATEGORY),
        )
        if source.primary_asset and source.primary_asset == candidate.primary_asset:
            matched.add("primary_asset")
        if set(source.confirmed_root_cause_categories) & set(candidate.confirmed_root_cause_categories):
            matched.add("confirmed_root_cause_categories")
        recurrence_type = next((kind for feature, kind in supported if feature in matched), None)
    if recurrence_type is None:
        return None
    return IncidentRecurrence(
        relationship_id=relationship_identity(
            source.tenant_id, source.environment, source.incident_id, candidate.incident_id, similarity.scoring_version
        ),
        tenant_id=source.tenant_id,
        environment=source.environment,
        current_incident_id=current.incident_id,
        prior_incident_id=prior.incident_id,
        recurrence_type=recurrence_type,
        confidence=similarity.confidence,
        similarity_score=similarity.similarity_score,
        evidence_coverage=similarity.evidence_coverage,
        reason_codes=similarity.reason_codes,
        signature_version=FAILURE_SIGNATURE_VERSION,
        scoring_version=similarity.scoring_version,
        feature_version=similarity.feature_version,
        first_seen_at=previous_at,
        previous_seen_at=previous_at,
    )
