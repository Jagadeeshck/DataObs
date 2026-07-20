from __future__ import annotations

from urllib.parse import urlencode, urlparse

DESTINATIONS = {
    "discover": "/app/discover",
    "observer_logs": "/app/discover",
    "infrastructure": "/app/metrics",
    "traces": "/app/apm/traces",
    "pathways": "/app/dashboards",
    "monitors": "/app/observability/alerts",
    "incidents": "/app/observability/cases",
    "workflows": "/app/management/insightsAndAlerting",
}


def kibana_link(base_url: str, destination: str, *, tenant: str, environment: str, resource_id: str) -> str:
    parsed = urlparse(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Kibana base URL must be an absolute HTTPS origin")
    if destination not in DESTINATIONS:
        raise ValueError("Kibana destination is not allowlisted")
    state = urlencode({"tenant": tenant, "environment": environment, "resource": resource_id})
    return f"{base_url.rstrip('/')}{DESTINATIONS[destination]}?{state}"
