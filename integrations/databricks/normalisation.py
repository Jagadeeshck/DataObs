from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

from packages.collectors.sdk import ResourceObservation

FORBIDDEN = frozenset(
    {
        "owner",
        "created_by",
        "updated_by",
        "storage_location",
        "storage_root",
        "access_point",
        "url",
        "host",
        "hostname",
        "http_path",
        "odbc_params",
        "jdbc_url",
        "creator_user_name",
        "run_as_user_name",
        "run_page_url",
        "notebook_path",
        "statement_text",
        "error_message",
        "executed_by",
        "executed_by_user_id",
        "session_id",
        "client_application",
        "query_tags",
        "source_ip",
        "parameters",
        "properties",
        "view_definition",
    }
)


def value(obj: object, name: str, default: Any = None) -> Any:
    return obj.get(name, default) if isinstance(obj, Mapping) else getattr(obj, name, default)


def allowlist(obj: object, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value(obj, field) for field in fields if value(obj, field) is not None and field not in FORBIDDEN}


def fingerprint(value_: str) -> str:
    return hashlib.sha256(value_.encode()).hexdigest()[:24]


def observation(
    context: Any, workspace_id: str, cloud: str, family: str, native_id: str, name: str, evidence: Mapping[str, Any]
) -> ResourceObservation:
    return ResourceObservation(
        "databricks",
        workspace_id,
        cloud,
        family,
        family,
        native_id,
        name[:256],
        datetime.now(timezone.utc),
        context.collection_run_id,
        source_evidence=evidence,
    )


SAFE_FIELDS = {
    "catalog": ("id", "name", "catalog_type", "browse_only", "provisioning_info", "created_at", "updated_at"),
    "schema": ("schema_id", "catalog_name", "name", "browse_only", "created_at", "updated_at"),
    "table": (
        "table_id",
        "catalog_name",
        "schema_name",
        "name",
        "full_name",
        "table_type",
        "data_source_format",
        "browse_only",
        "created_at",
        "updated_at",
    ),
    "volume": (
        "volume_id",
        "catalog_name",
        "schema_name",
        "name",
        "volume_type",
        "browse_only",
        "created_at",
        "updated_at",
    ),
    "warehouse": (
        "id",
        "name",
        "state",
        "cluster_size",
        "min_num_clusters",
        "max_num_clusters",
        "num_active_sessions",
        "auto_stop_mins",
        "enable_photon",
        "enable_serverless_compute",
        "channel",
        "spot_instance_policy",
        "warehouse_type",
        "health",
        "created_at",
    ),
    "job": (
        "job_id",
        "name",
        "created_time",
        "job_format",
        "trigger_type",
        "max_concurrent_runs",
        "timeout_seconds",
        "task_count",
        "job_cluster_count",
    ),
    "job_run": (
        "run_id",
        "job_id",
        "original_attempt_run_id",
        "run_type",
        "trigger",
        "life_cycle_state",
        "result_state",
        "start_time",
        "end_time",
        "setup_duration",
        "execution_duration",
        "cleanup_duration",
        "queue_duration",
        "attempt_number",
        "task_count",
        "repair_state",
    ),
}
