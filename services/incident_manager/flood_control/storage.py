from __future__ import annotations

from datetime import datetime
from typing import Any

from .contracts import FloodEvent, FloodState, FloodWindow
from .repository import StoredFlood

FLOOD_FIELDS = frozenset(
    {
        "id",
        "tenant_id",
        "environment",
        "correlation_id",
        "correlation_key",
        "correlation_version",
        "incident_id",
        "resource_ids",
        "affected_assets",
        "data_product_ids",
        "business_services",
        "severity",
        "occurrence_count",
        "first_observed_at",
        "last_observed_at",
        "created_at",
        "updated_at",
        "status",
        "metadata",
    }
)


def flood_to_document(stored: StoredFlood) -> dict[str, Any]:
    w, p = stored.window, stored.projection
    events = sorted(w.events.values(), key=lambda e: (e.occurred_at, e.event_id))[-100:]
    metadata = {
        **p,
        "flood_id": w.flood_id,
        "event_ids": [e.event_id for e in events],
        "event_times": [e.occurred_at.isoformat() for e in events],
        "event_incidents": [e.incident_id for e in events],
        "suppressed_notification_count": w.suppressed_notification_count,
        "last_transition_at": w.last_transition_at.isoformat() if w.last_transition_at else None,
    }
    return {
        "id": w.flood_id,
        "tenant_id": w.tenant_id,
        "environment": w.environment,
        "correlation_id": w.flood_id,
        "correlation_key": w.group_id,
        "correlation_version": str(p.get("policy_version", "v1")),
        "incident_id": str(p["representative_incident_id"]),
        "resource_ids": sorted({e.incident_id for e in events})[:100],
        "affected_assets": sorted({e.asset_id for e in events if e.asset_id})[:100],
        "data_product_ids": sorted({v for e in events for v in e.data_products})[:100],
        "business_services": sorted({v for e in events for v in e.business_services})[:100],
        "severity": str(p.get("highest_severity", "medium")),
        "occurrence_count": int(p.get("total_occurrence_count", len(events))),
        "first_observed_at": min(e.occurred_at for e in events).isoformat(),
        "last_observed_at": max(e.occurred_at for e in events).isoformat(),
        "created_at": str(p.get("created_at", min(e.occurred_at for e in events).isoformat())),
        "updated_at": max(e.occurred_at for e in events).isoformat(),
        "status": w.state.value,
        "metadata": metadata,
    }


def document_to_flood(source: dict[str, Any], seq_no: int, primary_term: int) -> StoredFlood:
    m = dict(source.get("metadata", {}))
    ids, times, incidents = m.pop("event_ids", []), m.pop("event_times", []), m.pop("event_incidents", [])
    events = {
        i: FloodEvent(i, datetime.fromisoformat(t), incident)
        for i, t, incident in zip(ids, times, incidents, strict=False)
    }
    transition = m.pop("last_transition_at", None)
    window = FloodWindow(
        source["correlation_id"],
        source["tenant_id"],
        source["environment"],
        source["correlation_key"],
        FloodState(source["status"]),
        events,
        int(m.pop("suppressed_notification_count", 0)),
        datetime.fromisoformat(transition) if transition else None,
    )
    return StoredFlood(window, m, seq_no, primary_term)
