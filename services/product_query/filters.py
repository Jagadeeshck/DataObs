from __future__ import annotations

from datetime import datetime
from typing import Any


def isolation_filters(tenant: str, environment: str, source: str | None = None) -> list[dict[str, Any]]:
    """Mandatory predicates for every shared Console projection read."""
    filters: list[dict[str, Any]] = [
        {"term": {"tenant_id": tenant}},
        {"term": {"environment": environment}},
    ]
    if source:
        filters.append({"term": {"integration_id": source}})
    return filters


def time_filter(start: datetime | None, end: datetime | None) -> dict[str, Any] | None:
    bounds = {key: value.isoformat() for key, value in (("gte", start), ("lte", end)) if value is not None}
    return {"range": {"@timestamp": bounds}} if bounds else None
