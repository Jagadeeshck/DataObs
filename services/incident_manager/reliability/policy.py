from __future__ import annotations

from .models import IncidentResponseObjectiveAssignment, IncidentResponseObjectiveDefinition


def select_definitions(
    definitions: list[IncidentResponseObjectiveDefinition],
    *,
    tenant_id: str,
    environment: str,
    severity: str | None,
    priority: str | None,
):
    """Apply trusted scope and bounded selectors; callers cannot supply scope via ES DSL."""
    return tuple(
        d
        for d in definitions
        if d.state == "active"
        and d.tenant_id == tenant_id
        and d.environment == environment
        and (not d.severity_selector or severity in d.severity_selector)
        and (not d.priority_selector or priority in d.priority_selector)
    )


def tighten_assignment(
    current: IncidentResponseObjectiveAssignment,
    proposed: IncidentResponseObjectiveAssignment,
    *,
    historical_breach: bool = False,
):
    """Severity changes may tighten, but never extend, a snapshotted deadline."""
    if current.incident_id != proposed.incident_id or current.metric_type != proposed.metric_type:
        raise ValueError("assignments do not describe the same incident objective metric")
    if historical_breach or proposed.deadline_at >= current.deadline_at:
        return current
    return proposed
