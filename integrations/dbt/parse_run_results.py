"""
Parse dbt run_results.json and emit OTel spans.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/29
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes

_tracer = trace.get_tracer("dataobs.dbt")

STATUS_TO_OTEL = {
    "success": trace.StatusCode.OK,
    "pass": trace.StatusCode.OK,
    "warn": trace.StatusCode.OK,
    "error": trace.StatusCode.ERROR,
    "fail": trace.StatusCode.ERROR,
    "skipped": trace.StatusCode.UNSET,
}


def parse_and_emit(run_results_path: str | Path) -> None:
    """
    Read dbt run_results.json and emit one OTel span per node.

    Args:
        run_results_path: Path to dbt target/run_results.json
    """
    path = Path(run_results_path)
    with path.open() as f:
        data: dict[str, Any] = json.load(f)

    metadata = data.get("metadata", {})
    results = data.get("results", [])

    with _tracer.start_as_current_span(
        "dbt.run",
        attributes={
            "dbt.invocation_id": metadata.get("invocation_id", "unknown"),
            "dbt.dbt_schema_version": metadata.get("dbt_schema_version", ""),
            "dbt.generated_at": metadata.get("generated_at", ""),
            SpanAttributes.DB_SYSTEM: metadata.get("adapter_type", "unknown"),
        },
    ):
        for result in results:
            _emit_node_span(result, metadata)


def _emit_node_span(result: dict[str, Any], metadata: dict[str, Any]) -> None:
    node = result.get("node", {})
    timing = result.get("timing", [{}])
    started_at = timing[0].get("started_at") if timing else None
    completed_at = timing[-1].get("completed_at") if timing else None

    status = result.get("status", "unknown")
    otel_status = STATUS_TO_OTEL.get(status, trace.StatusCode.UNSET)

    with _tracer.start_as_current_span(
        f"dbt.{node.get('resource_type', 'node')}",
        attributes={
            SpanAttributes.DB_SYSTEM: metadata.get("adapter_type", "unknown"),
            SpanAttributes.DB_SQL_TABLE: node.get("relation_name") or node.get("name", ""),
            "dbt.model.name": node.get("name", ""),
            "dbt.resource_type": node.get("resource_type", ""),
            "dbt.status": status,
            "dbt.materialization": node.get("config", {}).get("materialized", ""),
            "dbt.rows_affected": result.get("adapter_response", {}).get("rows_affected", 0),
            "dbt.started_at": started_at or "",
            "dbt.completed_at": completed_at or "",
        },
    ) as span:
        span.set_status(trace.Status(otel_status))
        if status in ("error", "fail"):
            span.add_event("dbt_failure", {"message": result.get("message", "")})
