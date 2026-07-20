from __future__ import annotations

from datetime import datetime, timezone

from packages.domain_model.incident import Incident, IncidentState

LEGAL_TRANSITIONS: dict[IncidentState, frozenset[IncidentState]] = {
    IncidentState.OPEN: frozenset({IncidentState.ACKNOWLEDGED, IncidentState.SUPPRESSED}),
    IncidentState.ACKNOWLEDGED: frozenset({IncidentState.INVESTIGATING, IncidentState.SUPPRESSED}),
    IncidentState.INVESTIGATING: frozenset(
        {
            IncidentState.MITIGATING,
            IncidentState.WAITING_FOR_APPROVAL,
            IncidentState.MONITORING_RECOVERY,
            IncidentState.SUPPRESSED,
        }
    ),
    IncidentState.MITIGATING: frozenset(
        {IncidentState.WAITING_FOR_APPROVAL, IncidentState.MONITORING_RECOVERY, IncidentState.INVESTIGATING}
    ),
    IncidentState.WAITING_FOR_APPROVAL: frozenset({IncidentState.MITIGATING, IncidentState.INVESTIGATING}),
    IncidentState.MONITORING_RECOVERY: frozenset({IncidentState.RESOLVED, IncidentState.INVESTIGATING}),
    IncidentState.RESOLVED: frozenset({IncidentState.CLOSED, IncidentState.REOPENED}),
    IncidentState.REOPENED: frozenset({IncidentState.INVESTIGATING, IncidentState.ACKNOWLEDGED}),
    IncidentState.SUPPRESSED: frozenset({IncidentState.OPEN, IncidentState.REOPENED}),
    IncidentState.CLOSED: frozenset({IncidentState.REOPENED}),
}

REASON_REQUIRED = frozenset(
    {IncidentState.SUPPRESSED, IncidentState.RESOLVED, IncidentState.CLOSED, IncidentState.REOPENED}
)


def transition(incident: Incident, state: IncidentState, *, reason: str | None = None) -> Incident:
    current = IncidentState(incident.incident_state)
    if state not in LEGAL_TRANSITIONS[current]:
        raise ValueError(f"illegal incident transition: {current.value} -> {state.value}")
    if state in REASON_REQUIRED and not (reason and reason.strip()):
        raise ValueError(f"reason is required for transition to {state.value}")
    now = datetime.now(timezone.utc)
    incident.incident_state = state
    incident.state_reason = reason
    incident.updated_at = now
    if state == IncidentState.ACKNOWLEDGED:
        incident.acknowledged_at = now
    if state == IncidentState.RESOLVED:
        incident.resolved_at = now
        incident.resolution_reason = reason
    if state == IncidentState.CLOSED:
        incident.closed_at = now
    if state == IncidentState.REOPENED:
        incident.reopened_at = now
        incident.resolved_at = None
        incident.closed_at = None
    return incident
