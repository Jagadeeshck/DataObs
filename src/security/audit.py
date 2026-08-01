"""Redaction-safe security event construction.

Security event callers cannot attach arbitrary request data.  This small fixed
schema is suitable for append-only persistence and deliberately excludes JWTs,
headers, claims, cookies, and bodies.
"""

from __future__ import annotations

from datetime import datetime, timezone

_MAX_FIELD = 256


def _bounded(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:_MAX_FIELD]


def security_event(
    *,
    event_type: str,
    outcome: str,
    reason_code: str,
    principal_id: str | None,
    tenant_id: str | None,
    environment: str | None,
    request_id: str,
    route_template: str,
    source_component: str = "dataobs-api",
) -> dict[str, str | None]:
    """Build the complete allowlisted v1 event envelope."""
    return {
        "schema_version": "1.0",
        "event_type": _bounded(event_type),
        "outcome": _bounded(outcome),
        "reason_code": _bounded(reason_code),
        "principal_id": _bounded(principal_id),
        "tenant_id": _bounded(tenant_id),
        "environment": _bounded(environment),
        "request_id": _bounded(request_id),
        "route_template": _bounded(route_template),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_component": _bounded(source_component),
    }
