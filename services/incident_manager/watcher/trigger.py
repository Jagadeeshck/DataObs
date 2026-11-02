"""Map a firing Elasticsearch watch into the existing incident pipeline event.

A watch, when it fires, POSTs a payload to the Team 3 internal webhook. This
module translates that payload into the normalized event shape consumed by
:meth:`IncidentManagerService.ingest`, which performs deduplication and drives
the existing notification dispatcher. Nothing here sends a notification or
performs remediation.

The mapper is deliberately strict and tenant-scoped: a watch whose payload
claims a different tenant than the authenticated webhook caller is rejected,
never silently re-homed.
"""

from __future__ import annotations

from typing import Any, Mapping


class WatchTriggerError(ValueError):
    """Raised when a firing-watch payload cannot be safely mapped."""


# Firing payloads carry a bare count/status; translate that into the
# ``event_type`` the normalizer already understands. A watch is an anomaly
# alert source, so it maps to the existing MONITOR_ANOMALY finding/signal.
_DEFAULT_EVENT_TYPE = "profile_anomaly"


def map_watch_firing_to_event(payload: Mapping[str, Any], *, tenant_id: str) -> dict[str, Any]:
    """Return a normalizer-ready event dict for a firing watch.

    ``payload`` is the body the watch action sent to the webhook. ``tenant_id``
    is the authenticated caller's tenant; it is authoritative and any
    conflicting tenant in the payload is rejected.
    """
    if not isinstance(payload, Mapping):
        raise WatchTriggerError("watch payload must be an object")

    watch_id = payload.get("watch_id") or payload.get("_watch_id")
    if not isinstance(watch_id, str) or not watch_id.strip():
        raise WatchTriggerError("watch_id is required")

    payload_tenant = payload.get("tenant_id")
    if payload_tenant is not None and payload_tenant != tenant_id:
        raise WatchTriggerError("cross-tenant watch firing rejected")

    # Only deliver when the watch condition actually met. A watch that reports
    # it did not fire must not open an incident (measured zero, not a signal).
    condition_met = payload.get("condition_met")
    if condition_met is False:
        raise WatchTriggerError("watch condition not met; nothing to deliver")

    asset_id = payload.get("asset_id") or payload.get("dataset") or payload.get("table")
    if not isinstance(asset_id, str) or not asset_id.strip():
        raise WatchTriggerError("asset_id is required to attribute the alert")

    monitor_id = payload.get("monitor_id")
    severity = payload.get("severity", "medium")

    event: dict[str, Any] = {
        "event_type": payload.get("event_type", _DEFAULT_EVENT_TYPE),
        "tenant_id": tenant_id,
        "environment": payload.get("environment", "default"),
        "asset_id": asset_id,
        "monitor_id": monitor_id,
        "severity": severity,
        "title": payload.get("title") or f"Watcher alert: {asset_id}",
        "summary": payload.get("summary")
        or payload.get("message")
        or f"Elasticsearch watch '{watch_id}' fired for {asset_id}",
        "alert_source": "elasticsearch_watcher",
        "source_event_id": watch_id,
        "id": payload.get("execution_id") or watch_id,
    }

    # Carry evidence/observed values through unchanged when provided, so the
    # incident reflects what the watch actually measured.
    if "observed_value" in payload:
        event["observed_value"] = payload["observed_value"]
    if "expected_value" in payload:
        event["expected_value"] = payload["expected_value"]
    if payload.get("evidence"):
        event["evidence"] = payload["evidence"]
    if payload.get("trace_id"):
        event["trace_id"] = payload["trace_id"]
    if payload.get("correlation_id"):
        event["correlation_id"] = payload["correlation_id"]

    return event
