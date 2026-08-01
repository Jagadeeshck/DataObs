from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from elasticsearch import Elasticsearch

from .manifest import (
    BASE_PROPERTIES,
    INCIDENT_AUTOMATION_PROPERTIES,
    KAFKA_PROPERTIES,
    MIGRATION_STATE_INDEX,
    SECURITY_PROPERTIES,
    migrations,
)

_DATA_PRODUCT_DECISION_INDEX = "dataobs-data-product-membership-decisions-v1"

PROVIDER_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "integration_id",
            "provider_type",
            "provider_version",
            "capability",
            "collection_run_id",
            "status",
            "evidence_status",
            "provider",
            "account",
            "region",
            "service",
            "resource_type",
            "native_resource_id",
            "display_name",
            "canonical_id",
            "owner",
            "resource_id",
            "metric_name",
            "state",
            "unit",
            "aggregation",
            "source_provider",
            "reason",
            "severity",
            "error_code",
        ]
    },
    **{key: {"type": "date"} for key in ["watermark", "started_at", "completed_at", "observed_at", "timestamp"]},
    **{
        key: {"type": "long"}
        for key in [
            "version",
            "resource_count",
            "observation_count",
            "skipped_duplicate_count",
            "retry_count",
            "partial_failure_count",
            "period_seconds",
            "freshness_seconds",
        ]
    },
    "value": {"type": "double"},
    "evidence_confidence": {"type": "double"},
    "scope": {"type": "flattened"},
    "source_evidence": {"type": "flattened"},
    "tags": {"type": "flattened"},
    "dimensions": {"type": "flattened"},
    "requested_capabilities": {"type": "keyword"},
    "completed_capabilities": {"type": "keyword"},
    "error_codes": {"type": "keyword"},
    "cursor": {"type": "keyword"},
    "configuration_fingerprint": {"type": "keyword"},
}


def plan() -> List[Dict[str, Any]]:
    return [
        {
            "migration_id": m.migration_id,
            "description": m.description,
            "schema_version": m.schema_version,
            "dependencies": m.dependencies,
            "checksum": m.checksum,
            "rollback_strategy": m.rollback_strategy,
            "operations": m.operations,
        }
        for m in migrations()
    ]


def _mapping() -> Dict[str, Any]:
    return {
        "dynamic": "strict",
        "properties": BASE_PROPERTIES
        | {
            "id": {"type": "keyword"},
            "name": {"type": "keyword"},
            "document": {"type": "flattened"},
            "lease_owner": {"type": "keyword"},
            "lease_expires_at": {"type": "date"},
            "idempotency_key": {"type": "keyword"},
            "fingerprint": {"type": "keyword"},
        }
        | INCIDENT_AUTOMATION_PROPERTIES
        | KAFKA_PROPERTIES
        | MONITORING_PROPERTIES
        | JOB_RUN_PROPERTIES
        | SECURITY_PROPERTIES
        | PROVIDER_PROPERTIES,
    }


MONITORING_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "path_id",
            "service_id",
            "product_id",
            "monitor_id",
            "monitor_type",
            "monitor_version",
            "baseline_method",
            "baseline_version",
            "sensitivity",
            "seasonality",
            "cold_start_state",
            "missing_data_state",
            "finding_severity",
            "recommendation_state",
            "coverage_state",
            "product_criticality",
            "hypothesis_type",
            "workflow_id",
            "incident_id",
            "investigation_id",
            "hypothesis_id",
        ]
    },
    **{key: {"type": "date"} for key in ["observation_timestamp", "evaluation_timestamp", "baseline_timestamp"]},
    **{
        key: {"type": "double"}
        for key in ["expected_minimum", "expected_maximum", "threshold", "anomaly_score", "confidence"]
    },
    "definition_revision": {"type": "integer"},
    "sample_count": {"type": "long"},
    "reliability_components": {"type": "flattened"},
    "supporting_evidence": {"type": "flattened"},
    "contradicting_evidence": {"type": "flattened"},
    "source_document_references": {"type": "keyword"},
}

JOB_RUN_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "source_integration",
            "qualified_name",
            "parent_run_id",
            "stage_id",
            "attempt_id",
            "source_native_id",
            "platform",
            "source_state",
            "state_reason",
            "code_version",
            "deployment_version",
            "config_version",
            "log_reference",
            "infrastructure_entity_reference",
            "failure_category",
            "error_fingerprint",
            "cost_status",
            "cost_estimation_method",
            "data_status",
            "rca_id",
            "streaming_query_id",
            "expected_run_id",
            "evaluation_id",
            "schedule_source",
            "schedule_kind",
            "reliability_state",
            "policy_owner",
            "schema_version",
        ]
    },
    **{
        key: {"type": "date"}
        for key in [
            "scheduled_at",
            "started_at",
            "ended_at",
            "ingested_at",
            "event_timestamp",
            "evaluation_timestamp",
            "permitted_start_at",
            "permitted_start_until",
            "deadline_at",
        ]
    },
    **{
        key: {"type": "long"}
        for key in [
            "queue_delay_ms",
            "schedule_delay_ms",
            "attempt_count",
            "input_records",
            "output_records",
            "input_bytes",
            "output_bytes",
            "critical_path_duration_ms",
            "policy_revision",
            "minimum_sample_size",
        ]
    },
    "input_asset_ids": {"type": "keyword"},
    "output_asset_ids": {"type": "keyword"},
    "resource_metrics": {"type": "flattened"},
    "openlineage_facets": {"type": "flattened"},
    "workflow_references": {"type": "keyword"},
    "incident_references": {"type": "keyword"},
    "reliability_score": {"type": "double"},
    "schedule_confidence": {"type": "double"},
    "evidence_confidence": {"type": "double"},
    "component_values": {"type": "flattened"},
    "component_weights": {"type": "flattened"},
    "reason_codes": {"type": "keyword"},
    "missing_inputs": {"type": "keyword"},
    "evidence_references": {"type": "keyword"},
}


def _ensure_mutable_index(es: Elasticsearch, index: str) -> None:
    if not es.indices.exists(index=index):
        es.indices.create(index=index, mappings=_mapping())
    es.indices.put_alias(index=index, name=f"{index}-read")
    es.indices.put_alias(index=index, name=f"{index}-write", is_write_index=True)


def _ensure_data_stream_template(es: Elasticsearch, pattern: str) -> None:
    name = f"dataobs-{pattern.replace('*','template').replace('.','-')}"
    properties = (
        BASE_PROPERTIES
        | INCIDENT_AUTOMATION_PROPERTIES
        | KAFKA_PROPERTIES
        | {
            **MONITORING_PROPERTIES,
            **JOB_RUN_PROPERTIES,
            **SECURITY_PROPERTIES,
            **PROVIDER_PROPERTIES,
            "event_type": {"type": "keyword"},
            "message": {"type": "match_only_text"},
            "metricset": {"type": "keyword"},
            "value": {"type": "double"},
        }
    )
    es.indices.put_index_template(
        name=name,
        index_patterns=[pattern],
        data_stream={},
        template={
            "mappings": {"dynamic": "strict", "properties": properties},
            "settings": {"index.default_pipeline": "none"},
        },
        priority=500,
        allow_auto_create=True,
    )


def _mapping_type_matches(expected: Dict[str, Any], installed: Dict[str, Any]) -> bool:
    """Compare the immutable portions of an explicit property definition."""
    if expected.get("type") != installed.get("type"):
        return False
    expected_fields = expected.get("fields", {})
    installed_fields = installed.get("fields", {})
    fields_match = all(
        name in installed_fields and _mapping_type_matches(definition, installed_fields[name])
        for name, definition in expected_fields.items()
    )
    expected_properties = expected.get("properties", {})
    installed_properties = installed.get("properties", {})
    return fields_match and all(
        name in installed_properties and _mapping_type_matches(definition, installed_properties[name])
        for name, definition in expected_properties.items()
    )


def _mapping_update_type_matches(
    index: str,
    field: str,
    expected: Dict[str, Any],
    installed: Dict[str, Any],
) -> bool:
    """Accept exact mappings plus one released, additive compatibility case.

    Migration 0015 installed the decision ``reason`` field as ``keyword`` and
    released migration 0016 described it as ``match_only_text``. Elasticsearch
    cannot change an existing field type. Migration 0018 therefore adds the
    canonical ``decision_reason`` field instead. Preserve the immutable legacy
    field while applying every other 0016 field and keep all unknown conflicts
    fail-closed.
    """
    if _mapping_type_matches(expected, installed):
        return True
    return (
        index == _DATA_PRODUCT_DECISION_INDEX
        and field == "reason"
        and expected.get("type") == "match_only_text"
        and installed.get("type") == "keyword"
    )


def _apply_mapping_update(es: Elasticsearch, index: str, properties: Dict[str, Any]) -> None:
    """Add and verify explicit fields on a trusted concrete product index."""
    registered_targets = {
        name for migration in migrations() for name in migration.operations.get("mapping_updates", {})
    }
    if index not in registered_targets:
        raise RuntimeError(f"Mapping migration targets an unregistered concrete index: {index}")
    if not es.indices.exists(index=index):
        raise RuntimeError(f"Required mapping target does not exist: {index}")
    current = es.indices.get_mapping(index=index)[index]["mappings"]
    if current.get("dynamic") != "strict":
        raise RuntimeError(f"Required strict mapping is not installed on {index}")
    current_properties = current.get("properties", {})
    conflicts = [
        name
        for name, definition in properties.items()
        if (
            name in current_properties
            and not _mapping_update_type_matches(index, name, definition, current_properties[name])
        )
    ]
    if conflicts:
        raise RuntimeError(f"Incompatible existing mapping on {index}: {', '.join(sorted(conflicts))}")
    missing_properties = {name: definition for name, definition in properties.items() if name not in current_properties}
    if missing_properties:
        es.indices.put_mapping(index=index, dynamic="strict", properties=missing_properties)
    installed = es.indices.get_mapping(index=index)[index]["mappings"]
    if installed.get("dynamic") != "strict" or any(
        name not in installed.get("properties", {})
        or not _mapping_update_type_matches(index, name, definition, installed["properties"][name])
        for name, definition in properties.items()
    ):
        raise RuntimeError(f"Mapping verification failed for {index}")


def _ensure_transform(es: Elasticsearch, definition: Any) -> None:
    # Older migrations carried name-only placeholders; 0007 definitions are executable latest transforms.
    if not isinstance(definition, dict):
        return
    transform_id = definition["id"]
    body = {
        "source": {"index": [definition["source"]]},
        "dest": {"index": definition["destination"]},
        "latest": {"unique_key": definition["unique_key"], "sort": definition["sort"]},
        "frequency": "1m",
        "sync": {"time": {"field": definition["sort"], "delay": "60s"}},
    }
    try:
        es.transform.get_transform(transform_id=transform_id)
    except Exception:
        es.transform.put_transform(transform_id=transform_id, **body)
    try:
        es.transform.start_transform(transform_id=transform_id)
    except Exception as exc:
        if "already started" not in str(exc).lower():
            raise


def _selected_migrations(through_migration_id: str | None = None) -> list[Any]:
    """Return a dependency-complete released prefix, optionally bounded by ID."""
    released = migrations()
    if through_migration_id is None:
        return released
    ids = [migration.migration_id for migration in released]
    if through_migration_id not in ids:
        raise ValueError(f"Unknown migration id: {through_migration_id}")
    selected = released[: ids.index(through_migration_id) + 1]
    selected_ids = {migration.migration_id for migration in selected}
    for migration in selected:
        missing = set(migration.dependencies) - selected_ids
        if missing:
            raise RuntimeError(
                f"Migration prefix through {through_migration_id} is dependency-invalid: "
                f"{migration.migration_id} requires {', '.join(sorted(missing))}"
            )
    return selected


def apply(es: Elasticsearch, *, through_migration_id: str | None = None) -> List[Dict[str, Any]]:
    if not es.indices.exists(index=MIGRATION_STATE_INDEX):
        es.indices.create(
            index=MIGRATION_STATE_INDEX,
            mappings={
                "dynamic": "strict",
                "properties": {
                    "migration_id": {"type": "keyword"},
                    "schema_version": {"type": "keyword"},
                    "checksum": {"type": "keyword"},
                    "applied_at": {"type": "date"},
                    "status": {"type": "keyword"},
                },
            },
        )
    applied = status(es).get("applied", {})
    out: list[dict[str, Any]] = []
    applied_ids: set[str] = set(applied)
    for m in _selected_migrations(through_migration_id):
        for dep in m.dependencies:
            if dep not in applied_ids:
                raise RuntimeError(f"Migration {m.migration_id} depends on unapplied {dep}")
        existing = applied.get(m.migration_id)
        if existing and existing.get("checksum") != m.checksum:
            raise RuntimeError(f"Checksum mismatch for {m.migration_id}")
        if existing:
            out.append(existing)
            applied_ids.add(m.migration_id)
            continue
        for index in m.operations.get("mutable_indices", []):
            _ensure_mutable_index(es, index)
        for pattern in m.operations.get("data_streams", []):
            _ensure_data_stream_template(es, pattern)
        for definition in m.operations.get("transforms", []):
            _ensure_transform(es, definition)
        for index, properties in m.operations.get("mapping_updates", {}).items():
            _apply_mapping_update(es, index, properties)
        for pattern, contract in m.operations.get("data_stream_contracts", {}).items():
            stem = pattern.replace("-*", "").replace(".", "-")
            component = f"dataobs-{stem}-mappings"
            policy = f"dataobs-{stem}-{contract['retention']}"
            es.ilm.put_lifecycle(
                name=policy,
                policy={
                    "phases": {
                        "hot": {"actions": {}},
                        "delete": {"min_age": contract["retention"], "actions": {"delete": {}}},
                    }
                },
            )
            es.cluster.put_component_template(
                name=component, template={"mappings": {"dynamic": "strict", "properties": contract["properties"]}}
            )
            es.indices.put_index_template(
                name=f"dataobs-{stem}-template",
                index_patterns=[pattern],
                data_stream={},
                composed_of=[component],
                priority=250,
                template={"settings": {"index.lifecycle.name": policy}},
            )
        doc = {
            "migration_id": m.migration_id,
            "schema_version": m.schema_version,
            "checksum": m.checksum,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "status": "applied",
        }
        es.index(index=MIGRATION_STATE_INDEX, id=m.migration_id, document=doc, refresh="wait_for")
        out.append(doc)
        applied_ids.add(m.migration_id)
    es.indices.refresh(index=MIGRATION_STATE_INDEX)
    return out


def status(es: Elasticsearch) -> Dict[str, Any]:
    required = {m.migration_id: m.checksum for m in migrations()}
    applied = {}
    if es.indices.exists(index=MIGRATION_STATE_INDEX):
        resp = es.search(index=MIGRATION_STATE_INDEX, query={"match_all": {}}, size=100)
        applied = {h["_source"]["migration_id"]: h["_source"] for h in resp["hits"]["hits"]}
    missing = [mid for mid in required if mid not in applied]
    checksum_mismatch = [
        mid for mid, checksum in required.items() if mid in applied and applied[mid].get("checksum") != checksum
    ]
    return {
        "required": list(required),
        "applied": applied,
        "missing": missing,
        "checksum_mismatch": checksum_mismatch,
        "ready": not missing and not checksum_mismatch,
    }


def rollback(es: Elasticsearch, migration_id: str = "0001_product_foundation") -> Dict[str, Any]:
    if es.indices.exists(index=MIGRATION_STATE_INDEX):
        es.delete(index=MIGRATION_STATE_INDEX, id=migration_id, ignore=[404])
    return {
        "migration_id": migration_id,
        "status": "rollback_record_removed",
        "strategy": "templates/indices are retained; remove manually after snapshot validation",
    }
