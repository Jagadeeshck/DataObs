"""Canonical, version-aware and safe dbt artifact normalisation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from .contracts import DbtArtifactEnvelope, NormalizedArtifact
from .errors import DbtArtifactError
from .identity import asset_identity, resource_id, run_identity
from .safety import ArtifactLimits, bounded_text, validate_safe
from .schemas import validate_schema_uri

RESOURCE_COLLECTIONS = {
    "nodes": {"model", "seed", "snapshot", "test"},
    "sources": {"source"},
    "exposures": {"exposure"},
    "metrics": {"metric"},
    "semantic_models": {"semantic_model"},
    "saved_queries": {"saved_query"},
    "groups": {"group"},
    "unit_tests": {"unit_test"},
}
SAFE_STATS = {"row_count", "bytes", "size_bytes", "non_null_count", "distinct_count"}


def _metadata(document: dict[str, Any], artifact_type: str) -> tuple[dict[str, Any], str]:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise DbtArtifactError("invalid_artifact", "Artifact metadata must be an object")
    version = validate_schema_uri(artifact_type, metadata.get("dbt_schema_version"))
    if not isinstance(metadata.get("dbt_version"), str) or not metadata["dbt_version"]:
        raise DbtArtifactError("invalid_artifact", "metadata.dbt_version is required")
    return metadata, version


def _dependencies(node: dict[str, Any], limits: ArtifactLimits) -> list[str]:
    depends = node.get("depends_on") or {}
    values = depends.get("nodes", []) if isinstance(depends, dict) else depends
    if not isinstance(values, list) or len(values) > limits.max_dependencies:
        raise DbtArtifactError("resource_limit_exceeded", "Resource dependency limit exceeded")
    return sorted(str(value)[:1024] for value in values)


def _columns(node: dict[str, Any], limits: ArtifactLimits) -> list[dict[str, Any]]:
    values = node.get("columns") or {}
    if not isinstance(values, dict) or len(values) > limits.max_columns:
        raise DbtArtifactError("resource_limit_exceeded", "Resource column limit exceeded")
    return [
        {
            "name": bounded_text(name, 512),
            "description": bounded_text(column.get("description"), limits.max_description),
            "data_type": bounded_text(column.get("data_type"), 256),
            "constraints": [str(item.get("type") if isinstance(item, dict) else item)[:128] for item in (column.get("constraints") or [])[:100]],
        }
        for name, column in sorted(values.items())
        if isinstance(column, dict)
    ]


def _safe_semantic_items(values: object, limits: ArtifactLimits) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    if len(values) > limits.max_columns:
        raise DbtArtifactError("resource_limit_exceeded", "Semantic item limit exceeded")
    return [
        {key: bounded_text(value.get(key), limits.max_description if key == "description" else 256)
         for key in ("name", "type", "role", "agg", "description") if value.get(key) is not None}
        for value in values if isinstance(value, dict)
    ]


def _resource(unique_id: str, node: dict[str, Any], envelope: DbtArtifactEnvelope, limits: ArtifactLimits) -> dict[str, Any]:
    resource_type = str(node.get("resource_type") or unique_id.split(".", 1)[0])
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    tags = node.get("tags") or []
    if not isinstance(tags, list) or len(tags) > limits.max_tags:
        raise DbtArtifactError("resource_limit_exceeded", "Resource tag limit exceeded")
    depends = _dependencies(node, limits)
    safe = {
        "resource_id": resource_id(envelope.tenant_id, envelope.environment, envelope.project_id, resource_type, unique_id),
        "asset_id": asset_identity(envelope.tenant_id, envelope.environment, envelope.project_id, resource_type, unique_id),
        "unique_id": unique_id[:1024], "resource_type": resource_type, "name": bounded_text(node.get("name"), 512),
        "package": bounded_text(node.get("package_name"), 512), "database": bounded_text(node.get("database"), 512),
        "schema": bounded_text(node.get("schema"), 512), "alias": bounded_text(node.get("alias"), 512),
        "description": bounded_text(node.get("description"), limits.max_description), "group": bounded_text(node.get("group"), 512),
        "tags": sorted(str(tag)[:256] for tag in tags), "dependencies": depends,
        "original_file_path": bounded_text(node.get("original_file_path"), 1024),
        "materialization": bounded_text(config.get("materialized"), 128),
        "incremental_strategy": bounded_text(config.get("incremental_strategy"), 128),
        "on_schema_change": bounded_text(config.get("on_schema_change"), 128),
        "columns": _columns(node, limits),
        "contract": {"enabled": bool((config.get("contract") or {}).get("enforced")), "alias_types": bool((config.get("contract") or {}).get("alias_types", True))},
        "entities": _safe_semantic_items(node.get("entities"), limits), "dimensions": _safe_semantic_items(node.get("dimensions"), limits),
        "measures": _safe_semantic_items(node.get("measures"), limits),
    }
    if resource_type == "saved_query":
        filter_value = node.get("where") or config.get("where")
        safe["has_filter"] = filter_value is not None
        safe["filter_fingerprint"] = hashlib.sha256(str(filter_value).encode()).hexdigest() if filter_value is not None else None
    if resource_type == "unit_test":
        given = node.get("given") or []
        safe["fixture_metadata"] = {"input_count": len(given), "fixture_fingerprint": hashlib.sha256(json.dumps(given, sort_keys=True).encode()).hexdigest()}
    safe["definition_fingerprint"] = hashlib.sha256(json.dumps(safe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return safe


def parse_manifest(document: dict[str, Any], envelope: DbtArtifactEnvelope, limits: ArtifactLimits) -> NormalizedArtifact:
    encoded = validate_safe(document, limits)
    metadata, version = _metadata(document, "manifest")
    resources: list[dict[str, Any]] = []
    for collection, allowed in RESOURCE_COLLECTIONS.items():
        values = document.get(collection) or {}
        if not isinstance(values, dict):
            raise DbtArtifactError("invalid_artifact", f"manifest.{collection} must be an object")
        for unique_id, node in values.items():
            if isinstance(node, dict) and str(node.get("resource_type") or unique_id.split(".", 1)[0]) in allowed:
                resources.append(_resource(str(unique_id), node, envelope, limits))
    if len(resources) > limits.max_resources:
        raise DbtArtifactError("resource_limit_exceeded", "Manifest resource limit exceeded")
    final = replace(envelope, artifact_schema_version=version, dbt_version=metadata["dbt_version"], invocation_id=str(metadata.get("invocation_id") or envelope.invocation_id)[:512], generated_at=metadata.get("generated_at"), artifact_fingerprint=hashlib.sha256(encoded).hexdigest())
    return NormalizedArtifact(final, tuple(resources))


def parse_artifact(document: dict[str, Any], envelope: DbtArtifactEnvelope, limits: ArtifactLimits | None = None) -> NormalizedArtifact:
    limits = limits or ArtifactLimits()
    if envelope.artifact_type == "manifest":
        return parse_manifest(document, envelope, limits)
    encoded = validate_safe(document, limits)
    metadata, version = _metadata(document, envelope.artifact_type)
    final = replace(envelope, artifact_schema_version=version, dbt_version=metadata["dbt_version"], invocation_id=str(metadata.get("invocation_id") or envelope.invocation_id)[:512], generated_at=metadata.get("generated_at"), artifact_fingerprint=hashlib.sha256(encoded).hexdigest())
    if envelope.artifact_type == "run_results":
        results = document.get("results") or []
        if not isinstance(results, list) or len(results) > limits.max_resources:
            raise DbtArtifactError("resource_limit_exceeded", "Run result limit exceeded")
        normalized = []
        statuses = {"success": "pass", "pass": "pass", "warn": "warn", "fail": "fail", "error": "error", "skipped": "skipped"}
        for result in results:
            if not isinstance(result, dict): continue
            response = result.get("adapter_response") or {}
            normalized.append({"unique_id": bounded_text(result.get("unique_id"), 1024), "run_id": run_identity(final.tenant_id, final.environment, final.project_id, final.invocation_id), "status": statuses.get(str(result.get("status")).lower(), "unknown"), "execution_time": result.get("execution_time") if isinstance(result.get("execution_time"), (int, float)) else None, "failure_count": result.get("failures") if isinstance(result.get("failures"), int) else None, "rows_affected": response.get("rows_affected") if isinstance(response, dict) and isinstance(response.get("rows_affected"), int) else None, "adapter_code": bounded_text(response.get("code"), 128) if isinstance(response, dict) else None})
        return NormalizedArtifact(final, executions=tuple(normalized))
    if envelope.artifact_type == "catalog":
        output = []
        for collection in ("nodes", "sources"):
            for unique_id, node in (document.get(collection) or {}).items():
                columns = node.get("columns") or {}
                output.append({"unique_id": str(unique_id)[:1024], "relation_type": bounded_text((node.get("metadata") or {}).get("type"), 128), "columns": [{"name": str(name)[:512], "index": col.get("index"), "type": bounded_text(col.get("type"), 256)} for name, col in list(columns.items())[:limits.max_columns]], "stats": {key: value.get("value") for key, value in (node.get("stats") or {}).items() if key in SAFE_STATS and isinstance(value, dict) and isinstance(value.get("value"), (int, float))}})
        return NormalizedArtifact(final, catalog=tuple(output))
    results = document.get("results") or []
    statuses = {"pass": "pass", "warn": "warn", "error": "error", "runtime error": "runtime_error"}
    output = tuple({"source_id": bounded_text(item.get("unique_id"), 1024), "status": statuses.get(str(item.get("status")).lower(), "unknown"), "max_loaded_at": item.get("max_loaded_at"), "snapshotted_at": item.get("snapshotted_at"), "max_loaded_at_age_seconds": item.get("max_loaded_at_time_ago_in_s"), "execution_time": item.get("execution_time")} for item in results if isinstance(item, dict))
    return NormalizedArtifact(final, freshness=output)


def normalize_dbt_event(value: dict[str, Any]) -> dict[str, Any]:
    """Compatibility normalizer for existing OpenLineage/dbt invocation callers."""
    invocation, unique_id = str(value.get("invocation_id") or "")[:512], str(value.get("unique_id") or "")[:1024]
    if not invocation or not unique_id: raise ValueError("dbt invocation_id and unique_id are required")
    code = value.get("compiled_code") or value.get("compiled_sql")
    return {"platform": "dbt", "invocation_id": invocation, "unique_id": unique_id, "resource_type": str(value.get("resource_type") or "unknown")[:128], "status": str(value.get("status") or "unknown")[:128], "compiled_code_fingerprint": hashlib.sha256(str(code).encode()).hexdigest() if code is not None else None, "depends_on": [str(x)[:1024] for x in value.get("depends_on", [])[:1000]]}
