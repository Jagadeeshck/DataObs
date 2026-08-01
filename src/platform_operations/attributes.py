"""Canonical low-cardinality metric attribute policy."""

ALLOWED_METRIC_ATTRIBUTES = frozenset(
    {
        "http.route",
        "http.request.method",
        "http.response.status_code_family",
        "dataobs.component",
        "dataobs.operation",
        "dataobs.outcome",
        "dataobs.error.category",
        "dataobs.provider.type",
        "dataobs.worker.type",
        "dataobs.lease.result",
        "dataobs.retry.result",
        "dataobs.auth.outcome",
        "dataobs.permission",
        "dataobs.dependency",
        "dataobs.snapshot.result",
        "dataobs.migration.result",
        "dataobs.release.decision_state",
    }
)
FORBIDDEN_FRAGMENTS = (
    "url",
    "query",
    "request_id",
    "trace_id",
    "span_id",
    "tenant",
    "email",
    "subject",
    "dataset",
    "table",
    "stream",
    "job_id",
    "run_id",
    "incident_id",
    "connector_id",
    "token",
    "exception",
    "sql",
    "body",
    "index",
)


def validate_metric_attributes(attributes: dict[str, object]) -> None:
    unknown = set(attributes) - ALLOWED_METRIC_ATTRIBUTES
    forbidden = {key for key in attributes if any(fragment in key.lower() for fragment in FORBIDDEN_FRAGMENTS)}
    if unknown or forbidden:
        raise ValueError(f"metric attributes violate policy: {sorted(unknown | forbidden)}")
    route = attributes.get("http.route")
    if route is not None and (
        "?" in str(route) or ("{" not in str(route) and any(part.isdigit() for part in str(route).split("/")))
    ):
        raise ValueError("http.route must be a stable route template")
