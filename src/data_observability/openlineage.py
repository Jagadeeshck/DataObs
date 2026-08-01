"""Bounded OpenLineage validation, redaction, and projection helpers."""

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
    "ABORT": "aborted",
    "OTHER": "unknown",
}
MAX_REQUEST_BYTES = 1_048_576
MAX_ARRAY_ITEMS = 1_000
MAX_STRING_LENGTH = 16_384
MAX_NESTING = 12
MAX_UNKNOWN_FACET_BYTES = 65_536
REDACTED_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "credential",
    "connection_string",
    "environment",
    "compiled_sql",
    "query",
    "stack_trace",
}
SAFE_FACETS = {
    "nominalTime",
    "parent",
    "ownership",
    "processingEngine",
    "jobType",
    "sourceCodeLocation",
    "documentation",
    "schema",
    "datasetType",
    "version",
    "dataQualityMetrics",
    "dataQualityAssertions",
    "columnLineage",
    "tags",
    "airflow",
    "dbt",
    "spark",
    "errorMessage",
}


class OpenLineageValidationError(ValueError):
    """Raised before unsafe OpenLineage content reaches persistence."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: object) -> str:
    material = "\x1f".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(material.encode()).hexdigest()}"


def qualified_name(namespace: str, name: str) -> str:
    return f"{namespace}:{name}"


def parse_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OpenLineageValidationError("eventTime must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise OpenLineageValidationError("eventTime must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise OpenLineageValidationError("eventTime must include a timezone")
    return parsed.astimezone(timezone.utc)


def duration_ms(start: str | None, finish: str | None) -> int | None:
    if not start or not finish:
        return None
    try:
        return max(0, int((parse_datetime(finish) - parse_datetime(start)).total_seconds() * 1000))
    except OpenLineageValidationError:
        return None


def _mapping(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OpenLineageValidationError(f"{field} must be an object")
    return dict(value)


def _validate_shape(value: Any, depth: int = 0) -> None:
    if depth > MAX_NESTING:
        raise OpenLineageValidationError("maximum payload nesting exceeded")
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        raise OpenLineageValidationError("maximum string size exceeded")
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS:
            raise OpenLineageValidationError("maximum array size exceeded")
        for item in value:
            _validate_shape(item, depth + 1)
    elif isinstance(value, Mapping):
        if len(value) > MAX_ARRAY_ITEMS:
            raise OpenLineageValidationError("maximum object size exceeded")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise OpenLineageValidationError("invalid object key")
            _validate_shape(item, depth + 1)


def _sensitive(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(name in lowered for name in REDACTED_KEYS)


def redact(value: Any, *, key: str = "") -> Any:
    if _sensitive(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def _datasets(value: Any, field: str) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OpenLineageValidationError(f"{field} must be an array")
    datasets = []
    for position, item in enumerate(value):
        dataset = _mapping(item, f"{field}[{position}]")
        for required in ("namespace", "name"):
            if not isinstance(dataset.get(required), str) or not dataset[required].strip():
                raise OpenLineageValidationError(f"{field}[{position}].{required} is required")
            dataset[required] = dataset[required].strip()
        datasets.append(dataset)
    return datasets


def canonical_event_id(payload: Mapping[str, Any]) -> str:
    supplied = payload.get("eventId")
    if supplied is not None:
        if not isinstance(supplied, str) or not supplied.strip():
            raise OpenLineageValidationError("eventId must be a non-empty string")
        return stable_id("ol_evt", supplied.strip())
    run: Mapping[str, Any] = payload.get("run") if isinstance(payload.get("run"), Mapping) else {}
    job: Mapping[str, Any] = payload.get("job") if isinstance(payload.get("job"), Mapping) else {}
    return stable_id(
        "ol_evt",
        payload.get("eventType"),
        payload.get("eventTime"),
        run.get("runId"),
        job.get("namespace"),
        job.get("name"),
    )


def parse_openlineage_event(
    payload: Dict[str, Any], *, tenant_id: str = "default", environment: str = "default"
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise OpenLineageValidationError("OpenLineage payload must be a JSON object")
    encoded = json.dumps(payload, separators=(",", ":"), default=str).encode()
    if len(encoded) > MAX_REQUEST_BYTES:
        raise OpenLineageValidationError("maximum request size exceeded")
    _validate_shape(payload)
    event_type = str(payload.get("eventType", "")).upper()
    if event_type not in VALID_EVENT_TYPES:
        raise OpenLineageValidationError("eventType must be one of: " + ", ".join(sorted(VALID_EVENT_TYPES)))
    event_time_raw = payload.get("eventTime")
    if not isinstance(event_time_raw, str):
        raise OpenLineageValidationError("eventTime must be a non-empty ISO-8601 timestamp")
    event_time = parse_datetime(event_time_raw).isoformat()
    run, job = _mapping(payload.get("run"), "run"), _mapping(payload.get("job"), "job")
    source_run_id = run.get("runId")
    if not isinstance(source_run_id, str) or not source_run_id.strip():
        raise OpenLineageValidationError("run.runId is required")
    namespace, name = job.get("namespace"), job.get("name")
    if not isinstance(namespace, str) or not namespace.strip():
        raise OpenLineageValidationError("job.namespace is required")
    if not isinstance(name, str) or not name.strip():
        raise OpenLineageValidationError("job.name is required")
    namespace, name, source_run_id = namespace.strip(), name.strip(), source_run_id.strip()
    producer = payload.get("producer")
    if not isinstance(producer, str) or not producer.strip():
        raise OpenLineageValidationError("producer is required")
    inputs, outputs = _datasets(payload.get("inputs", []), "inputs"), _datasets(payload.get("outputs", []), "outputs")
    groups = []
    for entity in (run, job, *inputs, *outputs):
        facets = entity.get("facets", {})
        if not isinstance(facets, Mapping):
            raise OpenLineageValidationError("facets must be objects")
        groups.append(facets)
    safe: Dict[str, Any] = {}
    unknown: Dict[str, Any] = {}
    for facets in groups:
        for facet_name, value in facets.items():
            (safe if facet_name in SAFE_FACETS else unknown)[facet_name] = redact(value, key=facet_name)
    if len(json.dumps(unknown, default=str).encode()) > MAX_UNKNOWN_FACET_BYTES:
        raise OpenLineageValidationError("maximum unknown-facet content exceeded")
    platform = infer_job_type(namespace)
    job_id = stable_id("job", tenant_id, environment, platform, namespace, name)
    run_id = stable_id("run", tenant_id, environment, platform, namespace, name, source_run_id)
    fingerprint = hashlib.sha256(
        json.dumps(redact(payload), sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return {
        "event_id": canonical_event_id(payload),
        "content_fingerprint": fingerprint,
        "event_type": event_type,
        "event_time": event_time,
        "status": EVENT_STATUS[event_type],
        "terminal": event_type in TERMINAL_EVENT_TYPES,
        "producer": producer.strip(),
        "schema_url": payload.get("schemaURL") or payload.get("schemaUrl") or "",
        "run_id": source_run_id,
        "canonical_run_id": run_id,
        "source_run_id": source_run_id,
        "run_facets": redact(dict(run.get("facets") or {})),
        "job_id": job_id,
        "job_qualified_name": qualified_name(namespace, name),
        "job_namespace": namespace,
        "job_name": name,
        "job_facets": redact(dict(job.get("facets") or {})),
        "safe_facets": safe,
        "unknown_facets": unknown,
        "tenant_id": tenant_id,
        "environment": environment,
        "platform": platform,
        "inputs": inputs,
        "outputs": outputs,
        "input_assets": [qualified_name(x["namespace"], x["name"]) for x in inputs],
        "output_assets": [qualified_name(x["namespace"], x["name"]) for x in outputs],
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
                # Transformation text can contain SQL and secrets.  Persist only
                # an evidence-safe classification and deterministic digest.
                transformation_fingerprint = hashlib.sha256(
                    json.dumps(transformations, sort_keys=True, separators=(",", ":"), default=str).encode()
                ).hexdigest()
                classification = "rename" if str(source_column) != str(target_column) else "identity"
                if transformations:
                    classification = "transformed"
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
                        "run_id": run_id,
                        "job_run_id": run_id,
                        "transformation_classification": classification,
                        "transformation_fingerprint": transformation_fingerprint,
                        "confidence": 0.9,
                        "evidence_refs": [],
                        "schema_version": "v1",
                        "observed_at": observed_at,
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
