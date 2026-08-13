"""Deterministic project health which excludes unavailable evidence."""

from typing import Any

WEIGHTS = {
    "run_reliability": 0.30,
    "test_health": 0.25,
    "source_freshness": 0.15,
    "contract_health": 0.10,
    "lineage_coverage": 0.10,
    "semantic_governance": 0.10,
}


def project_health(components: dict[str, float | None]) -> dict[str, Any]:
    available = {
        key: max(0.0, min(100.0, float(value)))
        for key, value in components.items()
        if key in WEIGHTS and value is not None
    }
    missing = sorted(set(WEIGHTS) - set(available))
    available_weight = sum(WEIGHTS[key] for key in available)
    if not available:
        return {
            "health_state": "unknown",
            "health_score": None,
            "confidence": 0.0,
            "components": {},
            "missing_components": missing,
            "reason_codes": ["no_health_evidence"],
            "weights": WEIGHTS,
            "available_weights": 0.0,
            "formula": "weighted mean of available components",
        }
    score = sum(available[key] * WEIGHTS[key] for key in available) / available_weight
    state = "healthy" if score >= 90 else "warning" if score >= 75 else "degraded" if score >= 50 else "critical"
    if missing and state == "healthy":
        state = "partial"
    return {
        "health_state": state,
        "health_score": round(score, 2),
        "confidence": round(available_weight, 2),
        "components": available,
        "missing_components": missing,
        "reason_codes": (["missing_components"] if missing else []),
        "weights": WEIGHTS,
        "available_weights": available_weight,
        "formula": "sum(component*weight)/available_weights",
    }
