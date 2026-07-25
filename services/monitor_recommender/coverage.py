from __future__ import annotations

from packages.domain_model.monitor import MonitorCoverage


def calculate_coverage(
    scope_type: str, scope_id: str, required: set[str], healthy: set[str], recommended: set[str] | None = None
) -> MonitorCoverage:
    recommended = recommended or set()
    if not required:
        state = "not_applicable"
    elif healthy >= required:
        state = "covered"
    elif healthy:
        state = "partially_covered"
    elif required & recommended:
        state = "recommended"
    else:
        state = "not_covered"
    gaps = sorted(required - healthy)
    return MonitorCoverage(
        scope_type=scope_type,
        scope_id=scope_id,
        state=state,
        numerator=len(required & healthy),
        denominator=len(required),
        high_risk_gaps=gaps,
        recommendation_count=len(required & recommended),
    )
