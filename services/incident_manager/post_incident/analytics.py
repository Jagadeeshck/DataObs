from __future__ import annotations

from datetime import datetime
from typing import Any

DEFINITION_VERSION = "incident-response-metrics/1.0.0"
STATES = frozenset(
    {"open", "acknowledged", "investigating", "mitigating", "waiting_for_approval", "monitoring_recovery", "resolved"}
)


def duration_metric(name: str, start: datetime | None, end: datetime | None) -> dict[str, Any]:
    status = "measured" if start is not None and end is not None and end >= start else "unavailable"
    return {
        "metric": name,
        "status": status,
        "value_ms": int((end - start).total_seconds() * 1000) if status == "measured" else None,
        "source_timestamps": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None},
        "definition_version": DEFINITION_VERSION,
    }


def state_durations(events: list[dict[str, Any]], cutoff: datetime | None = None) -> dict[str, int]:
    ordered = sorted(events, key=lambda event: (event["occurred_at"], event["event_id"]))
    totals: dict[str, int] = {}
    for current, following in zip(ordered, ordered[1:]):
        state = current.get("state")
        if state in STATES:
            totals[state] = totals.get(state, 0) + int(
                (following["occurred_at"] - current["occurred_at"]).total_seconds() * 1000
            )
    if ordered and cutoff and ordered[-1].get("state") in STATES and cutoff >= ordered[-1]["occurred_at"]:
        state = ordered[-1]["state"]
        totals[state] = totals.get(state, 0) + int((cutoff - ordered[-1]["occurred_at"]).total_seconds() * 1000)
    return totals


def build_projection(incident: Any, events: list[dict[str, Any]], *, computed_at: datetime) -> dict[str, Any]:
    opened = incident.opened_at
    reopened = [
        event for event in events if event.get("state") == "reopened" or event.get("event_type") == "incident_reopened"
    ]
    durations = state_durations(events, incident.closed_at or incident.resolved_at or computed_at)
    return {
        "tenant_id": incident.tenant_id,
        "environment": incident.environment,
        "incident_id": incident.id,
        "opened_at": opened,
        "severity": str(incident.severity),
        "priority": incident.priority,
        "time_to_acknowledge": duration_metric("time_to_acknowledge", opened, incident.acknowledged_at),
        "time_to_resolve": duration_metric("time_to_resolve", opened, incident.resolved_at),
        "time_to_close": duration_metric("time_to_close", opened, incident.closed_at),
        "signal_to_incident": duration_metric("signal_to_incident", incident.first_observed_at, opened),
        "state_durations_ms": durations,
        "waiting_for_approval_duration_ms": durations.get("waiting_for_approval"),
        "monitoring_recovery_duration_ms": durations.get("monitoring_recovery"),
        "reopen_count": len(reopened),
        "was_reopened": bool(reopened),
        "time_to_first_reopen": duration_metric(
            "time_to_first_reopen", opened, reopened[0]["occurred_at"] if reopened else None
        ),
        "has_recurrence": bool(incident.recurrence_of),
        "source_incident_revision": f"{incident.seq_no}:{incident.primary_term}",
        "source_timeline_checkpoint": max((event["event_id"] for event in events), default=None),
        "metric_definition_version": DEFINITION_VERSION,
        "projection_version": 1,
        "computed_at": computed_at,
    }
