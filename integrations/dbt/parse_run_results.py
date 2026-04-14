"""
Parse dbt run_results.json and emit OTel spans compliant with the
stable Database Semantic Conventions (db spans spec, stable as of v1.25+).

Spec: https://opentelemetry.io/docs/specs/semconv/db/database-spans/

Key semconv attributes used:
  db.system.name      — REQUIRED. DBMS product identifier (stable, replaces db.system)
  db.operation.name   — COND. REQUIRED. Operation being executed (e.g. "run_model", "test")
  db.collection.name  — COND. REQUIRED. Table/relation name (replaces db.sql.table)
  db.namespace        — COND. REQUIRED. Database name (schema/dataset)
  db.response.status_code — COND. REQUIRED on failure. dbt status string.
  db.query.summary    — RECOMMENDED. Low-cardinality summary of what ran.
  db.response.returned_rows — RECOMMENDED. rows_affected from adapter response.
  error.type          — COND. REQUIRED when operation failed.
  server.address      — RECOMMENDED. Target DB host (from dbt node config).
  SpanKind.CLIENT     — Required for all DB client spans.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/29
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

_tracer = trace.get_tracer("dataobs.dbt", "0.2.0")

# ── dbt adapter → db.system.name mapping ──────────────────────────────────────
# Values from: https://opentelemetry.io/docs/specs/semconv/db/database-spans/
# dbt adapters that map directly to semconv enum values:
_ADAPTER_TO_DB_SYSTEM: dict[str, str] = {
    "bigquery": "gcp.spanner",      # closest; BigQuery not in enum → use other_sql fallback below
    "snowflake": "other_sql",       # Snowflake not in semconv enum
    "redshift": "aws.redshift",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "trino": "trino",
    "spark": "other_sql",           # Spark SQL → other_sql
    "databricks": "other_sql",
    "duckdb": "other_sql",
    "mysql": "mysql",
    "sqlserver": "microsoft.sql_server",
    "athena": "other_sql",
    "clickhouse": "clickhouse",
    "teradata": "teradata",
}

# Override bigquery to other_sql — it has no semconv enum value yet
_ADAPTER_TO_DB_SYSTEM["bigquery"] = "other_sql"

# ── dbt resource_type → db.operation.name mapping ─────────────────────────────
_RESOURCE_TYPE_TO_OPERATION: dict[str, str] = {
    "model": "run_model",
    "test": "test",
    "seed": "seed",
    "snapshot": "snapshot",
    "analysis": "run_analysis",
    "exposure": "expose",
    "metric": "compute_metric",
    "source": "check_source",
    "rpc": "rpc",
    "run_result": "run",
}

# ── dbt status → OTel StatusCode ──────────────────────────────────────────────
_STATUS_TO_OTEL_CODE: dict[str, StatusCode] = {
    "success": StatusCode.OK,
    "pass": StatusCode.OK,
    "warn": StatusCode.OK,       # warning = not an error in OTel terms
    "error": StatusCode.ERROR,
    "fail": StatusCode.ERROR,
    "runtime error": StatusCode.ERROR,
    "skipped": StatusCode.UNSET,
    "no_results": StatusCode.UNSET,
}

# dbt statuses that represent a failure and should set error.type
_ERROR_STATUSES = frozenset({"error", "fail", "runtime error"})


def parse_and_emit(run_results_path: str | Path) -> list[str]:
    """
    Read dbt ``target/run_results.json`` and emit one OTel span per node result.

    Returns:
        List of span names emitted (useful for testing without a real exporter).

    Raises:
        FileNotFoundError: If run_results_path does not exist.
        ValueError: If the file does not match the expected dbt v4/v5 schema.
    """
    path = Path(run_results_path)
    with path.open() as f:
        data: dict[str, Any] = json.load(f)

    _validate_schema(data)

    metadata: dict[str, Any] = data.get("metadata", {})
    results: list[dict[str, Any]] = data.get("results", [])
    elapsed_seconds: float = data.get("elapsed_time", 0.0)

    adapter_type: str = metadata.get("adapter_type", "")
    db_system_name: str = _resolve_db_system(adapter_type)
    invocation_id: str = metadata.get("invocation_id", "unknown")

    span_names: list[str] = []

    # Root span — one per dbt invocation
    root_span_name = f"dbt run {db_system_name}"
    with _tracer.start_as_current_span(
        root_span_name,
        kind=SpanKind.CLIENT,
        attributes={
            # --- Stable DB semconv ---
            "db.system.name": db_system_name,
            "db.operation.name": "run",
            "db.query.summary": f"dbt run ({len(results)} nodes)",
            # --- dbt-specific (custom namespace) ---
            "dbt.invocation_id": invocation_id,
            "dbt.schema_version": metadata.get("dbt_schema_version", ""),
            "dbt.generated_at": metadata.get("generated_at", ""),
            "dbt.elapsed_time_seconds": elapsed_seconds,
            "dbt.node_count": len(results),
        },
    ):
        span_names.append(root_span_name)
        for result in results:
            name = _emit_node_span(result, metadata, db_system_name)
            span_names.append(name)

    return span_names


def _emit_node_span(
    result: dict[str, Any],
    metadata: dict[str, Any],
    db_system_name: str,
) -> str:
    """Emit one CLIENT span for a single dbt node result."""
    node: dict[str, Any] = result.get("node", {})
    resource_type: str = node.get("resource_type", "")
    status: str = result.get("status", "unknown")
    adapter_response: dict[str, Any] = result.get("adapter_response", {}) or {}

    # ── Semconv: db.operation.name ─────────────────────────────────────────────
    db_operation_name = _resolve_operation_name(resource_type, node)

    # ── Semconv: db.collection.name ────────────────────────────────────────────
    # Prefer relation_name (fully-qualified), fall back to node name.
    db_collection_name = _resolve_collection_name(node)

    # ── Semconv: db.namespace ──────────────────────────────────────────────────
    # dbt "schema" (e.g. "analytics", "dbt_prod") maps to db.namespace.
    db_namespace = node.get("schema") or node.get("database") or ""

    # ── Semconv: db.response.status_code ──────────────────────────────────────
    # dbt status string is the closest analogue to a DB response code.
    db_response_status_code: Optional[str] = status if status != "unknown" else None

    # ── Semconv: db.response.returned_rows ────────────────────────────────────
    rows_affected: int = adapter_response.get("rows_affected", 0) or 0

    # ── Semconv: span name = "{db.operation.name} {db.collection.name}" ───────
    if db_collection_name:
        span_name = f"{db_operation_name} {db_collection_name}"
    else:
        span_name = db_operation_name

    # ── Timing ────────────────────────────────────────────────────────────────
    timing: list[dict[str, Any]] = result.get("timing", []) or []
    started_at: str = timing[0].get("started_at", "") if timing else ""
    completed_at: str = timing[-1].get("completed_at", "") if timing else ""
    execution_time: float = result.get("execution_time", 0.0) or 0.0

    # ── Build attribute dict — only include non-empty values ──────────────────
    attrs: dict[str, Any] = {
        # Required / conditionally required (stable spec)
        "db.system.name": db_system_name,
        "db.operation.name": db_operation_name,
    }
    if db_collection_name:
        attrs["db.collection.name"] = db_collection_name
    if db_namespace:
        attrs["db.namespace"] = db_namespace
    if db_response_status_code:
        attrs["db.response.status_code"] = db_response_status_code
    if rows_affected:
        attrs["db.response.returned_rows"] = rows_affected

    # Recommended
    attrs["db.query.summary"] = _build_query_summary(db_operation_name, db_collection_name, node)

    # Server address (dbt target host if available)
    server_addr = node.get("config", {}).get("target", {})
    if isinstance(server_addr, dict) and server_addr.get("host"):
        attrs["server.address"] = server_addr["host"]

    # dbt-specific custom attributes (prefixed dbt.*)
    attrs.update({
        "dbt.model.name": node.get("name", ""),
        "dbt.resource_type": resource_type,
        "dbt.status": status,
        "dbt.materialization": node.get("config", {}).get("materialized", ""),
        "dbt.unique_id": node.get("unique_id", ""),
        "dbt.package_name": node.get("package_name", ""),
        "dbt.path": node.get("original_file_path", ""),
        "dbt.started_at": started_at,
        "dbt.completed_at": completed_at,
        "dbt.execution_time_seconds": execution_time,
        # Adapter metadata (low-cardinality values only)
        "dbt.adapter.code": str(adapter_response.get("_message", "")
                               or adapter_response.get("code", ""))[:256],
    })

    # error.type — conditionally required when operation failed
    if status in _ERROR_STATUSES:
        attrs["error.type"] = f"dbt.{status}"

    otel_status_code = _STATUS_TO_OTEL_CODE.get(status, StatusCode.UNSET)

    with _tracer.start_as_current_span(
        span_name,
        kind=SpanKind.CLIENT,
        attributes=attrs,
    ) as span:
        span.set_status(Status(otel_status_code))

        # Capture failure message as span event + exception
        if status in _ERROR_STATUSES:
            failure_message = result.get("message", "") or ""
            span.add_event(
                "dbt.failure",
                attributes={
                    "dbt.status": status,
                    "message": failure_message[:1024],  # cap length
                    "dbt.unique_id": node.get("unique_id", ""),
                },
            )
            # Also record as exception so it surfaces in error tracking
            span.record_exception(
                RuntimeError(failure_message or f"dbt {status}: {node.get('name', 'unknown')}")
            )

        # Attach test sub-results as events (dbt test failures contain sub-failures)
        for sub in result.get("failures", []) or []:
            span.add_event("dbt.test_failure", {"details": str(sub)[:512]})

    return span_name


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_db_system(adapter_type: str) -> str:
    """Map dbt adapter name to semconv db.system.name value."""
    if not adapter_type:
        return "other_sql"
    return _ADAPTER_TO_DB_SYSTEM.get(adapter_type.lower(), "other_sql")


def _resolve_operation_name(resource_type: str, node: dict[str, Any]) -> str:
    """Derive db.operation.name from dbt resource_type."""
    if resource_type == "test":
        # dbt tests are either generic or singular — distinguish if possible
        test_type = node.get("test_metadata", {}).get("name", "")
        if test_type:
            return f"test.{test_type}"
        return "test"
    return _RESOURCE_TYPE_TO_OPERATION.get(resource_type, resource_type or "run")


def _resolve_collection_name(node: dict[str, Any]) -> str:
    """
    Derive db.collection.name from dbt node.

    Prefers the fully-qualified relation_name (e.g. ``mydb.analytics.orders``),
    falls back to node name. Strips surrounding quotes.
    """
    relation = node.get("relation_name") or ""
    if relation:
        return relation.strip('"').strip("`")
    return node.get("name", "")


def _build_query_summary(operation: str, collection: str, node: dict[str, Any]) -> str:
    """
    Build a low-cardinality db.query.summary string.

    Pattern: "{operation} {collection}" (matches semconv span name recommendation).
    """
    parts = [operation]
    if collection:
        parts.append(collection)
    return " ".join(parts)


# ── Schema validation ─────────────────────────────────────────────────────────

#: Fields required in the top-level run_results.json document.
_REQUIRED_TOP_LEVEL = frozenset({"metadata", "results"})
#: Fields required in each result entry.
_REQUIRED_RESULT_FIELDS = frozenset({"status", "unique_id", "timing"})
#: Fields required inside the nested metadata block.
_REQUIRED_METADATA_FIELDS = frozenset({"dbt_schema_version", "invocation_id"})

#: Schema versions this parser understands.
_SUPPORTED_SCHEMA_VERSIONS = frozenset({
    "https://schemas.getdbt.com/dbt/run-results/v4/run-results.json",
    "https://schemas.getdbt.com/dbt/run-results/v5/run-results.json",
    "https://schemas.getdbt.com/dbt/run-results/v6/run-results.json",
})


def _validate_schema(data: dict[str, Any]) -> None:
    """
    Validate that *data* conforms to the expected dbt run_results.json schema.

    Raises:
        ValueError: With a descriptive message when validation fails.
    """
    # Top-level required fields
    missing_top = _REQUIRED_TOP_LEVEL - data.keys()
    if missing_top:
        raise ValueError(
            f"run_results.json missing required top-level fields: {sorted(missing_top)}"
        )

    # metadata block
    metadata = data["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("run_results.json 'metadata' must be a dict")

    missing_meta = _REQUIRED_METADATA_FIELDS - metadata.keys()
    if missing_meta:
        raise ValueError(
            f"run_results.json metadata missing fields: {sorted(missing_meta)}"
        )

    # Schema version check (warn but don't fail on unknown versions)
    schema_version = metadata.get("dbt_schema_version", "")
    if schema_version and schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
        import warnings
        warnings.warn(
            f"Unrecognised dbt run_results schema version: {schema_version!r}. "
            f"Supported: {sorted(_SUPPORTED_SCHEMA_VERSIONS)}. Parsing anyway.",
            UserWarning,
            stacklevel=4,
        )

    # results list
    results = data["results"]
    if not isinstance(results, list):
        raise ValueError("run_results.json 'results' must be a list")

    for idx, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError(f"results[{idx}] must be a dict, got {type(result).__name__}")
        missing_result = _REQUIRED_RESULT_FIELDS - result.keys()
        if missing_result:
            raise ValueError(
                f"results[{idx}] missing required fields: {sorted(missing_result)}"
            )
        if not isinstance(result["timing"], list):
            raise ValueError(f"results[{idx}].timing must be a list")
