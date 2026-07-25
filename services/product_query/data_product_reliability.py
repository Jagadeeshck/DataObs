from __future__ import annotations

from packages.domain_model.data_product import DataProductReliability


def score_reliability(
    values: dict[str, float | None], weights: dict[str, float], observed_period: str
) -> DataProductReliability:
    present = {key: value for key, value in values.items() if value is not None and key in weights}
    missing = sorted(key for key, value in values.items() if value is None)
    observed_weight = sum(weights[key] for key in present)
    score = (
        None
        if not observed_weight
        else round(sum(float(value) * weights[key] for key, value in present.items()) / observed_weight, 2)
    )
    confidence = round(observed_weight / sum(weights.values()), 4) if weights else 0.0
    state = "unknown" if score is None else "healthy" if score >= 90 else "at_risk" if score >= 70 else "unhealthy"
    return DataProductReliability(
        component_values=values,
        component_weights=weights,
        missing_components=missing,
        confidence=confidence,
        observed_period=observed_period,
        overall_score=score,
        overall_state=state,
    )
