from __future__ import annotations

import re
from typing import Any

SECRET = re.compile(r"(authorization|bearer|token|secret|password|credential|api[_-]?key)", re.I)
MAX_SUMMARY = 500
MAX_METADATA_VALUE = 256


def _bounded(value: object) -> str:
    text = str(value)
    return "[redacted]" if SECRET.search(text) else text[:MAX_METADATA_VALUE]


def timeline_event_to_document(event: dict[str, Any]) -> dict[str, Any]:
    """Translate a domain event into fields admitted by the released strict stream."""
    metadata = {
        "actor": _bounded(event["actor"]),
        "event_type": _bounded(event["event_type"]),
    }
    return {
        "@timestamp": event["timestamp"],
        "tenant_id": event["tenant_id"],
        "environment": event["environment"],
        "incident_id": event["incident_id"],
        "correlation_id": event["event_id"],
        "event_type": _bounded(event["event_type"]),
        "request_id": event.get("request_id"),
        "summary": _bounded(event.get("summary", ""))[:MAX_SUMMARY],
        "revision": int(event["revision"]),
        "metadata": metadata,
    }


def timeline_document_to_event(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata") or {}
    return {
        "event_id": document["correlation_id"],
        "event_type": document.get("event_type") or metadata.get("event_type", "unknown"),
        "timestamp": document["@timestamp"],
        "actor": metadata.get("actor", "unknown"),
        "summary": document.get("summary", ""),
        "revision": int(document.get("revision", 0)),
        "request_id": document.get("request_id"),
    }
