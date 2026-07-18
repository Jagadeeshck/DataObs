from __future__ import annotations

from datetime import datetime, timezone

from packages.domain_model.incident import Incident, IncidentState


def transition(incident: Incident, state: IncidentState, *, reason: str | None = None) -> Incident:
    now = datetime.now(timezone.utc)
    incident.incident_state = state
    incident.updated_at = now
    if state == IncidentState.ACKNOWLEDGED:
        incident.acknowledged_at = now
    if state == IncidentState.RESOLVED:
        incident.resolved_at = now
        incident.resolution_reason = reason
    if state == IncidentState.CLOSED:
        incident.closed_at = now
    return incident
