from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .features import FEATURE_VERSION, IncidentFeatures
from .fingerprint import incident_fingerprint
from .models import FeatureMatch, IncidentSimilarity, SimilarityClassification

SCORING_VERSION = "incident-similarity/1.0.0"
DISPLAY_THRESHOLD = 0.30
HIGH_THRESHOLD = 0.72
RECURRENCE_CANDIDATE_THRESHOLD = 0.82
MIN_RECURRENCE_CONFIDENCE = 0.65
MIN_RECURRENCE_FAMILIES = 3


@dataclass(frozen=True)
class FeaturePolicy:
    name: str
    method: Literal["exact", "jaccard"]
    weight: float
    reliability: float
    missing_policy: str = "unavailable"


FEATURE_POLICIES = (
    FeaturePolicy("primary_asset", "exact", 0.16, 0.95),
    FeaturePolicy("affected_assets", "jaccard", 0.10, 0.90),
    FeaturePolicy("finding_types", "jaccard", 0.11, 0.90),
    FeaturePolicy("signal_types", "jaccard", 0.05, 0.85),
    FeaturePolicy("resource_ids", "jaccard", 0.06, 0.90),
    FeaturePolicy("rule_ids", "jaccard", 0.13, 0.98),
    FeaturePolicy("failure_categories", "jaccard", 0.13, 0.90),
    FeaturePolicy("correlation_keys", "jaccard", 0.05, 0.95),
    FeaturePolicy("correlation_feature_keys", "jaccard", 0.04, 0.70),
    FeaturePolicy("data_product_ids", "jaccard", 0.07, 0.85),
    FeaturePolicy("business_services", "jaccard", 0.03, 0.75),
    FeaturePolicy("confirmed_root_cause_categories", "jaccard", 0.04, 1.00),
    FeaturePolicy("recovery_characteristics", "jaccard", 0.03, 0.65),
)
assert round(sum(policy.weight for policy in FEATURE_POLICIES), 10) == 1.0


def _compare(a: object, b: object, method: str) -> float | None:
    if method == "exact":
        return None if a is None or b is None else float(a == b)
    left, right = set(a or ()), set(b or ())
    if not left or not right:
        return None
    return len(left & right) / len(left | right)


def _classification(score: float, coverage: float) -> SimilarityClassification:
    if coverage < 0.20:
        return SimilarityClassification.INSUFFICIENT_EVIDENCE
    if score >= 0.85:
        return SimilarityClassification.VERY_HIGH
    if score >= HIGH_THRESHOLD:
        return SimilarityClassification.HIGH
    if score >= 0.45:
        return SimilarityClassification.MODERATE
    return SimilarityClassification.LOW


def score_similarity(
    source: IncidentFeatures, candidate: IncidentFeatures, *, computed_at: datetime | None = None
) -> IncidentSimilarity:
    if source.tenant_id != candidate.tenant_id:
        raise ValueError("cross-tenant similarity is prohibited")
    if source.environment != candidate.environment:
        raise ValueError("cross-environment similarity is prohibited")
    available_weight = score_sum = reliability_sum = 0.0
    matched: list[FeatureMatch] = []
    different: list[FeatureMatch] = []
    unavailable: list[str] = []
    for policy in FEATURE_POLICIES:
        value = _compare(getattr(source, policy.name), getattr(candidate, policy.name), policy.method)
        if value is None:
            unavailable.append(policy.name)
            continue
        available_weight += policy.weight
        score_sum += policy.weight * value
        reliability_sum += policy.weight * policy.reliability
        item = FeatureMatch(feature=policy.name, weight=policy.weight, match=policy.method, similarity=value)
        (matched if value > 0 else different).append(item)
    coverage = available_weight
    score = score_sum / available_weight if available_weight else 0.0
    independent_matches = sum(item.similarity > 0 for item in matched)
    reliability = reliability_sum / available_weight if available_weight else 0.0
    breadth = min(1.0, independent_matches / MIN_RECURRENCE_FAMILIES)
    confidence = coverage * reliability * (0.5 + 0.5 * breadth)
    return IncidentSimilarity(
        source_incident_id=source.incident_id,
        candidate_incident_id=candidate.incident_id,
        similarity_score=round(score, 6),
        evidence_coverage=round(coverage, 6),
        confidence=round(confidence, 6),
        classification=_classification(score, coverage),
        feature_version=FEATURE_VERSION,
        scoring_version=SCORING_VERSION,
        matched_features=matched,
        different_features=different,
        unavailable_features=unavailable,
        reason_codes=[f"same_{item.feature}" for item in matched if item.similarity == 1],
        computed_at=computed_at or datetime.now(timezone.utc),
        source_revision=source.source_revision,
        candidate_revision=candidate.source_revision,
        same_structural_signature=incident_fingerprint(source) == incident_fingerprint(candidate),
    )
