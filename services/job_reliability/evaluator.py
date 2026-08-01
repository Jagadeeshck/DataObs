"""Explainable reliability scoring; unavailable evidence is never a measured zero."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Optional

from packages.domain_model.job_run import JobReliabilitySnapshot, ReliabilityPolicy, ReliabilityState


def calculate_reliability(
    policy: ReliabilityPolicy,
    components: Mapping[str, Optional[float]],
    sample_counts: Mapping[str, int],
    evaluated_from: datetime,
    evaluated_until: datetime,
    *,
    schedule_confidence: float = 1.0,
    observed_at: Optional[datetime] = None,
) -> JobReliabilitySnapshot:
    """Normalize configured weights over evidenced components and return the formula inputs."""
    available = {name: value for name, value in components.items() if value is not None}
    for name, value in available.items():
        if not 0 <= value <= 1:
            raise ValueError(f"component {name} must be between 0 and 1")
    eligible = {
        name: value for name, value in available.items() if sample_counts.get(name, 0) >= policy.minimum_sample_size
    }
    weights = {name: policy.component_weights.get(name, 1.0) for name in eligible}
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("component weights cannot be negative")
    weight_total = sum(weights.values())
    normalized = {name: weight / weight_total for name, weight in weights.items()} if weight_total else {}
    enough = len(eligible) >= policy.minimum_available_components and bool(normalized)
    score = sum(eligible[name] * weight for name, weight in normalized.items()) * 100 if enough else None
    coverage = len(eligible) / max(len(components), 1)
    sample_coverage = (
        min(1.0, min(sample_counts.get(n, 0) for n in eligible) / policy.minimum_sample_size) if eligible else 0
    )
    confidence = max(0.0, min(1.0, coverage * sample_coverage * schedule_confidence))
    if not policy.enabled:
        state = ReliabilityState.DISABLED
    elif score is None:
        state = ReliabilityState.NO_DATA
    elif confidence < 0.5:
        state = ReliabilityState.WARNING
    elif score >= policy.minimum_success_rate * 100:
        state = ReliabilityState.HEALTHY
    elif score >= policy.minimum_success_rate * 90:
        state = ReliabilityState.WARNING
    else:
        state = ReliabilityState.BREACHING
    missing = sorted(set(components) - set(eligible))
    reasons = (["insufficient_sample_size"] if score is None else []) + (["partial_evidence"] if missing else [])
    return JobReliabilitySnapshot(
        tenant_id=policy.tenant_id,
        environment=policy.environment,
        job_id=policy.job_id,
        state=state,
        score=score,
        components=dict(components),
        normalized_weights=normalized,
        sample_counts=dict(sample_counts),
        evaluated_from=evaluated_from,
        evaluated_until=evaluated_until,
        confidence=confidence,
        missing_components=missing,
        reason_codes=reasons,
        policy_revision=policy.revision,
        observed_at=observed_at or evaluated_until,
    )
