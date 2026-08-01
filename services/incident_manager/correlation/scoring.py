from __future__ import annotations

from dataclasses import replace

from .contracts import EvidenceState, FeatureResult
from .policy import CorrelationPolicy


def score(
    features: tuple[FeatureResult, ...], policy: CorrelationPolicy
) -> tuple[float, float, tuple[FeatureResult, ...]]:
    available = [f for f in features if f.state not in {EvidenceState.UNAVAILABLE, EvidenceState.UNSUPPORTED}]
    evaluated_weight = sum(policy.weights.get(f.name, 0) for f in available)
    enriched = tuple(
        replace(f, contribution=policy.weights.get(f.name, 0) if f.state == EvidenceState.MATCHED else 0)
        for f in features
    )
    total = sum(f.contribution for f in enriched)
    coverage = evaluated_weight / max(sum(policy.weights.values()), 0.0001)
    confidence = min(1.0, total * coverage / max(policy.minimum_score, 0.0001))
    return round(total, 6), round(confidence, 6), enriched
