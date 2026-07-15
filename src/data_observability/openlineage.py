"""OpenLineage parsing and projection helpers for DataObs.

The module intentionally depends only on the Python standard library so the
DataObs API can receive OpenLineage events without coupling ingestion to a
specific OpenLineage client release. Unknown facets are preserved verbatim and
stored using Elasticsearch ``flattened`` mappings.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping

VALID_EVENT_TYPES = {"START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"}
TERMINAL_EVENT_TYPES = {"COMPLETE", "FAIL", "ABORT"}
EVENT_STATUS = {
    "START": "running",
    "RUNNING": "running",
    "COMPLETE": "success",
    "FAIL": "failed",
    "ABORT": "failed",
    "OTHER": "unknown",
}


class OpenLineageValidationError(ValueError):
    """Raised when a payload is not a valid OpenLineage RunEvent subset."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: object) -> str:
    material = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def qualified_name(namespace: str, name: str) -> str:
    return f"{namespace}:{name}"


def parse_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OpenLineageValidationError("eventTime must be a non-empty ISO-8601 timestamp")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OpenLineageValidationError("eventTime must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def duration_ms(start: str | None, finish: str | None) -> int:
    if not start or not finish:
        return 0
    try:
        delta = parse_datetime(finish) - parse_datetime(start)
    except OpenLineageValidationError:
        return 0
    return max(0, int(delta.total_seconds() * 1000))


def _mapping(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OpenLineageValidationError(f"{field} must be an object")
    return dict(value)


def _datasets(value: Any, field: str) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OpenLineageValidationError(f"{field} must be an array")
    datasets: List[Dict[str, Any]] = []
    for position, item in enumerate(value):
        dataset = _mapping(item, f"{field}[{position}]")
        namespace = dataset.get("namespace")
        name = dataset.get("name")
        if not isinstance(namespace, str) or not namespace.strip():
            raise OpenLineageValidationError(f"{field}[{position}].namespace is required")
        if not isinstance(name, str) or not name.strip():
            raise OpenLineageValidationError(f"{field}[{position}].name is required")
        dataset["namespace"] = namespace.strip()
        dataset["name"] = name.strip()
        datasets.append(dataset)
    return datasets


def canonical_event_id(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return stable_id("ol_evt", canonical)


def parse_openlineage_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalise an OpenLineage RunEvent.

    DataObs currently projects RunEvent payloads. JobEvent and DatasetEvent can
    still be retained later because the raw event document stores the original
    body without mapping every custom facet.
    """

    if not isinstance(payload, dict):
        raise OpenLineageValidationError("OpenLineage payload must be a JSON object")

    event_type = str(payload.get("eventType", "")).upper()
    if event_type not in VALID_EVENT_TYPES:
        allowed = ", ".join(sorted(VALID_EVENT_TYPES))
        raise OpenLineageValidationError(f"eventType must be one of: {allowed}")

    event_time_raw = payload.get("eventTime")
    event_time = parse_datetime(event_time_raw).isoformat()

    run = _mapping(payload.get("run"), "run")
    run_id = run.get("runId")
    if not isinstance(run_id, str) or not run_id.strip():
        raise OpenLineageValidationError("run.runId is required")
    run_id = run_id.strip()

    job = _mapping(payload.get("job"), "job")
    job_namespace = job.get("namespace")
    job_name = job.get("name")
    if not isinstance(job_namespace, str) or not job_namespace.strip():
        raise OpenLineageValidationError("job.namespace is required")
    if not isinstance(job_name, str) or not job_name.strip():
        raise OpenLineageValidationError("job.name is required")
    job_namespace = job_namespace.strip()
    job_name = job_name.strip()

    inputs = _datasets(payload.get("inputs", []), "inputs")
    outputs = _datasets(payload.get("outputs", []), "outputs")
    input_assets = [qualified_name(dataset["namespace"], dataset["name"]) for dataset in inputs]
    output_assets = [qualified_name(dataset["namespace"], dataset["name"]) for dataset in outputs]

    return {
        "event_id": canonical_event_id(payload),
        "event_type": event_type,
        "event_time": event_time,
        "status": EVENT_STATUS[event_type],
        "terminal": event_type in TERMINAL_EVENT_TYPES,
        "producer": payload.get("producer", "unknown"),
        "schema_url": payload.get("schemaURL") or payload.get("schemaUrl") or "",
        "run_id": run_id,
        "run_facets": dict(run.get("facets") or {}),
        "job_id": stable_id("job", job_namespace, job_name),
        "job_qualified_name": qualified_name(job_namespace, job_name),
        "job_namespace": job_namespace,
        "job_name": job_name,
        "job_facets": dict(job.get("facets") or {}),
        "inputs": inputs,
        "outputs": outputs,
        "input_assets": input_assets,
        "output_assets": output_assets,
    }


def infer_job_type(namespace: str) -> str:
    lowered = namespace.lower()
    for candidate in ("airflow", "spark", "dbt", "flink", "glue", "databricks", "dagster"):
        if candidate in lowered:
            return candidate
    return "openlineage"


def _facet(dataset: Mapping[str, Any], name: str) -> Dict[str, Any]:
    facets = dataset.get("facets") or {}
    value = facets.get(name) if isinstance(facets, Mapping) else None
    return dict(value) if isinstance(value, Mapping) else {}


def _first_owner(dataset: Mapping[str, Any]) -> str | None:
    owners = _facet(dataset, "ownership").get("owners") or []
    if isinstance(owners, list):
        for owner in owners:
            if isinstance(owner, Mapping) and owner.get("name"):
                return str(owner["name"])
    return None


def _tags(dataset: Mapping[str, Any]) -> List[str]:
    values = _facet(dataset, "tags").get("tags") or []
    tags: List[str] = []
    if isinstance(values, list):
        for value in values:
            if isinstance(value, Mapping):
                tag = value.get("key") or value.get("name")
            else:
                tag = value
            if tag:
                tags.append(str(tag))
    return tags


def dataset_projection(dataset: Dict[str, Any], observed_at: str) -> Dict[str, Any]:
    namespace = dataset["namespace"]
    name = dataset["name"]
    asset_id = qualified_name(namespace, name)
    documentation = _facet(dataset, "documentation")
    dataset_type = _facet(dataset, "datasetType")
    version = _facet(dataset, "version")
    metrics = _facet(dataset, "dataQualityMetrics")
    return {
        "asset_id": asset_id,
        "canonical_id": stable_id("dataset", namespace, name),
        "qualified_name": asset_id,
        "namespace": namespace,
        "name": name,
        "asset_type": dataset_type.get("datasetType") or "table",
        "source_system": namespace,
        "owner": _first_owner(dataset),
        "tags": _tags(dataset),
        "description": documentation.get("description"),
        "dataset_version": version.get("datasetVersion"),
        "row_count": metrics.get("rowCount"),
        "byte_count": metrics.get("bytes"),
        "file_count": metrics.get("fileCount"),
        "data_quality_metrics": metrics or None,
        "facets": dict(dataset.get("facets") or {}),
        "last_seen_at": observed_at,
    }


def _type_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "unknown"
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def schema_columns(dataset: Dict[str, Any], observed_at: str) -> List[Dict[str, Any]]:
    asset_id = qualified_name(dataset["namespace"], dataset["name"])
    fields = _facet(dataset, "schema").get("fields") or []
    if not isinstance(fields, list):
        return []
    columns: List[Dict[str, Any]] = []
    for position, field in enumerate(fields):
        if not isinstance(field, Mapping) or not field.get("name"):
            continue
        column_name = str(field["name"])
        columns.append(
            {
                "column_id": stable_id("column", asset_id, column_name),
                "asset_id": asset_id,
                "column_name": column_name,
                "data_type": _type_text(field.get("type")),
                "description": field.get("description", ""),
                "ordinal_position": position,
                "updated_at": observed_at,
            }
        )
    return columns


def column_lineage_edges(
    outputs: Iterable[Dict[str, Any]],
    *,
    job_id: str,
    run_id: str,
    observed_at: str,
) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    for output in outputs:
        target_asset_id = qualified_name(output["namespace"], output["name"])
        fields = _facet(output, "columnLineage").get("fields") or {}
        if not isinstance(fields, Mapping):
            continue
        for target_column, lineage in fields.items():
            if not isinstance(lineage, Mapping):
                continue
            input_fields = lineage.get("inputFields") or []
            if not isinstance(input_fields, list):
                continue
            for input_field in input_fields:
                if not isinstance(input_field, Mapping):
                    continue
                namespace = input_field.get("namespace")
                name = input_field.get("name")
                source_column = input_field.get("field")
                if not namespace or not name or not source_column:
                    continue
                source_asset_id = qualified_name(str(namespace), str(name))
                transformations = input_field.get("transformations") or []
                edge_id = stable_id(
                    "column_edge",
                    source_asset_id,
                    source_column,
                    target_asset_id,
                    target_column,
                    job_id,
                )
                edges.append(
                    {
                        "edge_id": edge_id,
                        "source_asset_id": source_asset_id,
                        "source_column": str(source_column),
                        "target_asset_id": target_asset_id,
                        "target_column": str(target_column),
                        "job_id": job_id,
                        "job_run_id": run_id,
                        "transformations": transformations,
                        "first_seen": observed_at,
                        "last_seen": observed_at,
                        "active": True,
                    }
                )
    return edges


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def quality_assertion_runs(
    datasets: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    observed_at: str,
) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    for dataset in datasets:
        asset_id = qualified_name(dataset["namespace"], dataset["name"])
        assertions = _facet(dataset, "dataQualityAssertions").get("assertions") or []
        if not isinstance(assertions, list):
            continue
        for position, assertion in enumerate(assertions):
            if not isinstance(assertion, Mapping):
                continue
            assertion_type = str(assertion.get("assertion") or "custom_metric")
            name = str(assertion.get("name") or f"{assertion_type}_{position}")
            check_id = stable_id("quality_check", asset_id, name, assertion.get("column", ""))
            success = bool(assertion.get("success"))
            configured_severity = str(assertion.get("severity") or "error").lower()
            severity = "warning" if configured_severity == "warn" else "critical"
            quality_run_id = stable_id("quality_run", run_id, asset_id, name, position)
            runs.append(
                {
                    "run_id": quality_run_id,
                    "source_run_id": run_id,
                    "check_id": check_id,
                    "asset_id": asset_id,
                    "check_type": assertion_type,
                    "column_name": assertion.get("column"),
                    "status": "pass" if success else ("warning" if severity == "warning" else "failed"),
                    "observed_value": _number(assertion.get("actual")),
                    "expected_value": _number(assertion.get("expected")),
                    "severity": severity,
                    "message": assertion.get("description") or name,
                    "details": dict(assertion),
                    "started_at": observed_at,
                    "finished_at": observed_at,
                    "duration_ms": 0,
                }
            )
    return runs
