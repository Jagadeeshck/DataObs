from __future__ import annotations

from packages.domain_model.incident import Finding, Severity

_WEIGHTS = {Severity.LOW: 10, Severity.MEDIUM: 30, Severity.HIGH: 60, Severity.CRITICAL: 90}


def calculate_severity(finding: Finding, *, recurrence: int = 1) -> tuple[Severity, dict[str, float | int | str]]:
    score = float(_WEIGHTS[Severity(finding.severity)])
    factors: dict[str, float | int | str] = {"finding_severity": str(finding.severity), "base_score": score}
    if finding.environment in {"prod", "production"}:
        score += 10
        factors["production_environment"] = 10
    impact = min(finding.downstream_asset_count * 2, 20)
    score += impact
    factors["downstream_impact"] = impact
    recurrence_bonus = min(max(recurrence - 1, 0) * 3, 15)
    score += recurrence_bonus
    factors["recurrence"] = recurrence_bonus
    confidence_adjustment = (finding.confidence - 1.0) * 20
    score += confidence_adjustment
    factors["confidence_adjustment"] = round(confidence_adjustment, 2)
    factors["total_score"] = round(score, 2)
    if score >= 85:
        return Severity.CRITICAL, factors
    if score >= 60:
        return Severity.HIGH, factors
    if score >= 30:
        return Severity.MEDIUM, factors
    return Severity.LOW, factors
