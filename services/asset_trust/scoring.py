"""Deterministic Asset Trust Score v1 calculation."""

from __future__ import annotations

import json
from hashlib import sha256

from packages.domain_model.asset_trust import (
    DIMENSIONS,
    AssetTrustDimension,
    AssetTrustEvidence,
    AssetTrustPolicy,
    AssetTrustScore,
    score_identity,
)

SOURCE_RANK = {"production_slo": 30, "canonical_domain": 20, "canonical_evaluation": 10}


def deduplicate_evidence(evidence: list[AssetTrustEvidence]) -> list[AssetTrustEvidence]:
    """Prefer the highest canonical layer and remove shared provenance globally.

    Global provenance is intentional: an SLO derived from a freshness monitor or a
    producer-job evaluation must not amplify the same failure in two dimensions.
    """
    selected: list[AssetTrustEvidence] = []
    claimed: set[str] = set()
    candidates = sorted(
        evidence,
        key=lambda e: (-SOURCE_RANK.get(e.evidence_source, 0), DIMENSIONS.index(e.dimension), e.evidence_ref),
    )
    for item in candidates:
        provenance = set(item.derived_from) | {item.evidence_ref}
        if provenance & claimed:
            continue
        selected.append(item)
        claimed |= provenance
    return selected


def calculate_asset_trust(
    *,
    tenant_id: str,
    environment: str,
    asset_id: str,
    evidence: list[AssetTrustEvidence],
    policy: AssetTrustPolicy,
    window_start,
    window_end,
    calculated_at=None,
) -> AssetTrustScore:
    chosen = deduplicate_evidence(evidence)
    dimensions, missing, stale = [], [], []
    reason_codes: list[str] = []
    for name in DIMENSIONS:
        weight = policy.dimension_weights.get(name, 0)
        items = [e for e in chosen if e.dimension == name]
        current = [e for e in items if e.status == "observed" and e.score is not None]
        stale_items = [e for e in items if e.status == "stale"]
        if stale_items:
            stale.append(name)
        if not current:
            missing.append(name)
            dimension = AssetTrustDimension(
                name=name,
                score=None,
                weight=weight,
                weighted_score=None,
                status="unknown",
                confidence=0,
                coverage=0,
                evidence_status="stale" if stale_items else "missing",
                evidence_refs=[e.evidence_ref for e in items],
                reason_codes=["evidence.stale" if stale_items else "evidence.missing"],
                observed_at=max((e.observed_at for e in items), default=None),
            )
        else:
            component = sum(e.score * e.confidence for e in current) / sum(e.confidence for e in current)
            confidence = sum(e.confidence for e in current) / len(current)
            coverage = sum(e.coverage for e in current) / len(current)
            codes = sorted({code for e in current for code in e.reason_codes})
            reason_codes.extend(codes)
            dimension = AssetTrustDimension(
                name=name,
                score=component,
                weight=weight,
                weighted_score=component * weight,
                status="healthy" if component >= 80 else "degraded",
                confidence=confidence,
                coverage=coverage,
                evidence_status="observed",
                evidence_refs=[e.evidence_ref for e in current],
                reason_codes=codes,
                positive_factors=codes if component >= 80 else [],
                negative_factors=codes if component < 80 else [],
                observed_at=max(e.observed_at for e in current),
            )
        dimensions.append(dimension)
    eligible = [d for d in dimensions if d.score is not None and d.weight > 0]
    available_weight = sum(d.weight for d in eligible)
    uncapped = None if not available_weight else sum(d.score * d.weight for d in eligible) / available_weight
    coverage = sum(d.weight * d.coverage for d in dimensions)
    freshness_factor = (
        0 if not eligible else sum(d.weight * (0 if d.name in stale else 1) for d in eligible) / available_weight
    )
    source_factor = 0 if not eligible else sum(d.weight * d.confidence for d in eligible) / available_weight
    confidence = coverage * freshness_factor * source_factor
    final, cap_reason = uncapped, None
    for cap in sorted(policy.critical_caps, key=lambda c: c.maximum_score):
        matching = [
            e for e in chosen if cap.reason_code in e.reason_codes and e.confidence >= cap.minimum_evidence_confidence
        ]
        if matching and final is not None and final > cap.maximum_score:
            final, cap_reason = cap.maximum_score, cap.reason_code
            break
    required_missing = sorted(set(policy.required_dimensions) & set(missing))
    if final is None:
        state = "unknown"
    elif confidence < policy.minimum_confidence or required_missing:
        state = "partial"
    else:
        thresholds = policy.state_thresholds
        state = next((s for s in ("strong", "healthy", "attention", "poor") if final >= thresholds[s]), "critical")
    payload = sorted((e.evidence_ref, e.score, e.status, e.observed_at.isoformat()) for e in chosen)
    fingerprint = sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
    observed_at = max((e.observed_at for e in chosen), default=window_end)
    positives = [f for d in dimensions for f in d.positive_factors]
    negatives = [f for d in dimensions for f in d.negative_factors]
    return AssetTrustScore(
        score_id=score_identity(
            tenant_id, environment, asset_id, window_start, window_end, policy.policy_id, policy.version, fingerprint
        ),
        tenant_id=tenant_id,
        environment=environment,
        asset_id=asset_id,
        score=final,
        state=state,
        confidence=confidence,
        evidence_coverage=coverage,
        dimensions=dimensions,
        missing_dimensions=missing,
        stale_dimensions=stale,
        reason_codes=sorted(set(reason_codes + ([cap_reason] if cap_reason else []))),
        top_positive_factors=positives[:3],
        top_negative_factors=negatives[:3],
        evidence_refs=sorted(e.evidence_ref for e in chosen),
        policy_id=policy.policy_id,
        policy_version=policy.version,
        window_start=window_start,
        window_end=window_end,
        observed_at=observed_at,
        calculated_at=calculated_at or window_end,
        formula="sum(component_score * weight) / available_weight",
        available_weight=available_weight,
        uncapped_score=uncapped,
        cap_applied=cap_reason is not None,
        cap_reason=cap_reason,
        evidence_fingerprint=fingerprint,
    )


def attribute_change(previous: AssetTrustScore, current: AssetTrustScore) -> list[dict[str, float | str]]:
    before = {d.name: d for d in previous.dimensions}
    changes = []
    for dimension in current.dimensions:
        old = before.get(dimension.name)
        if old and old.score is not None and dimension.score is not None:
            changes.append(
                {
                    "dimension": dimension.name,
                    "contribution": round((dimension.score - old.score) * dimension.weight, 4),
                }
            )
    return sorted(changes, key=lambda item: (-abs(float(item["contribution"])), str(item["dimension"])))
