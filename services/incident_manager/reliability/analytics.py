from __future__ import annotations

ALLOWED_GROUPS = {"severity", "priority", "business_service", "data_product"}
MAX_RANGE_DAYS = 366


def aggregation_body(*, tenant_id: str, environment: str, start: str, end: str, group_by: str | None = None) -> dict:
    """Build the server-owned ES aggregation used by reliability APIs."""
    if group_by is not None and group_by not in ALLOWED_GROUPS:
        raise ValueError("unsupported reliability group_by")
    aggs = {
        "acknowledgement_percentiles": {
            "percentiles": {"field": "acknowledgement_actual_ms", "percents": [50, 90, 95]}
        },
        "resolution_percentiles": {"percentiles": {"field": "resolution_actual_ms", "percents": [50, 90, 95]}},
        "mean_acknowledgement": {"avg": {"field": "acknowledgement_actual_ms"}},
        "mean_resolution": {"avg": {"field": "resolution_actual_ms"}},
        "objective_breaches": {"sum": {"field": "response_objective_breach_count"}},
        "status_counts": {
            "filters": {
                "filters": {
                    "open": {"term": {"is_open": True}},
                    "reopened": {"term": {"was_reopened": True}},
                    "confirmed_recurrence": {"term": {"confirmed_recurrence": True}},
                }
            }
        },
    }
    if group_by:
        aggs["breakdown"] = {"terms": {"field": group_by, "size": 50}}
    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"tenant_id": tenant_id}},
                    {"term": {"environment": environment}},
                    {"range": {"opened_at": {"gte": start, "lt": end}}},
                ]
            }
        },
        "aggs": aggs,
    }
