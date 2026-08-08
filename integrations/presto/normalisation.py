from datetime import datetime, timezone

from packages.collectors.sdk import ResourceObservation

CONNECTOR_CATEGORIES = {
    "hive": "hive/lakehouse",
    "iceberg": "iceberg",
    "kafka": "kafka",
    "mysql": "relational",
    "postgresql": "relational",
    "sqlserver": "relational",
    "mongodb": "object/other",
}


def connector_category(name):
    return CONNECTOR_CATEGORIES.get(str(name).lower(), "unknown")


def resource(context, cluster, family, native, evidence):
    safe = dict(evidence)
    for forbidden in ("query", "user", "source", "node_id", "http_uri", "task_id", "stage_id"):
        safe.pop(forbidden, None)
    if family == "catalogs" and "connector_name" in safe:
        safe["connector_category"] = connector_category(safe["connector_name"])
    if family == "runtime_queries":
        safe["history_completeness"] = "bounded_runtime_history"
    return ResourceObservation(
        "presto",
        cluster,
        "global",
        "sql_engine",
        family,
        native,
        native,
        datetime.now(timezone.utc),
        context.collection_run_id,
        source_evidence=safe,
    )
