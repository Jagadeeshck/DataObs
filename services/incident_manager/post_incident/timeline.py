from __future__ import annotations

from typing import Any

CATEGORY = {
    "incident_created": "detection",
    "incident_acknowledged": "response",
    "approval_requested": "approval",
    "incident_resolved": "recovery",
    "incident_reopened": "lifecycle",
    "incident_closed": "lifecycle",
}


def assemble(events: list[dict[str, Any]], limit: int = 200) -> list[dict[str, Any]]:
    if not 1 <= limit <= 500:
        raise ValueError("timeline limit out of bounds")
    normalized = []
    for event in events[:500]:
        kind = str(event.get("event_type", "unknown"))
        normalized.append(
            {
                "event_id": str(event["event_id"]),
                "occurred_at": event.get("occurred_at", event.get("timestamp")),
                "event_type": kind,
                "category": CATEGORY.get(kind, "investigation"),
                "actor_type": str(event.get("actor_type", "system")),
                "actor_ref": event.get("actor_ref"),
                "summary": str(event.get("summary", kind.replace("_", " ")))[:500],
                "evidence_refs": list(event.get("evidence_refs", ()))[:20],
                "importance": "automatic" if kind in CATEGORY else "normal",
            }
        )
    return sorted(normalized, key=lambda item: (item["occurred_at"], item["event_id"]))[:limit]
