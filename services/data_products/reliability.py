"""Evidence-honest Data Product reliability calculation."""

from __future__ import annotations

from math import isfinite

from packages.domain_model.data_product import DataProductReliability


def calculate_reliability(
    values: dict[str, float | None], weights: dict[str, float], *, observed_period: str, stale: set[str] | None = None
) -> DataProductReliability:
    stale = stale or set()
    if any(not isfinite(weight) or weight < 0 for weight in weights.values()):
        raise ValueError("component weights must be finite and non-negative")
    if any(value is not None and (not isfinite(value) or not 0 <= value <= 1) for value in values.values()):
        raise ValueError("component values must be finite and between zero and one")
    missing = sorted(name for name, value in values.items() if value is None)
    observed = {
        name: value
        for name, value in values.items()
        if value is not None and name not in stale and weights.get(name, 0) > 0
    }
    denominator = sum(weights[name] for name in observed)
    total_weight = sum(weight for weight in weights.values() if weight > 0)
    score = (
        None
        if denominator == 0
        else sum(float(value) * weights[name] for name, value in observed.items()) / denominator
    )
    confidence = 0.0 if total_weight == 0 else denominator / total_weight
    if score is None:
        state = "unknown"
    elif score >= 0.95:
        state = "healthy"
    elif score >= 0.8:
        state = "at_risk"
    else:
        state = "unhealthy"
    return DataProductReliability(
        component_values=values,
        component_weights=weights,
        missing_components=missing,
        stale_components=sorted(stale),
        confidence=confidence,
        observed_period=observed_period,
        overall_score=score,
        overall_state=state,
    )
