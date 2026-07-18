from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from elasticsearch import Elasticsearch

from .manifest import BASE_PROPERTIES, INCIDENT_AUTOMATION_PROPERTIES, MIGRATION_STATE_INDEX, migrations


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
        | INCIDENT_AUTOMATION_PROPERTIES,
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
        | {
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


def apply(es: Elasticsearch) -> List[Dict[str, Any]]:
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
    for m in migrations():
        for dep in m.dependencies:
            if dep not in applied_ids:
                raise RuntimeError(f"Migration {m.migration_id} depends on unapplied {dep}")
        existing = applied.get(m.migration_id)
        if existing and existing.get("checksum") != m.checksum:
            raise RuntimeError(f"Checksum mismatch for {m.migration_id}")
        for index in m.operations.get("mutable_indices", []):
            _ensure_mutable_index(es, index)
        for pattern in m.operations.get("data_streams", []):
            _ensure_data_stream_template(es, pattern)
        if existing:
            out.append(existing)
        else:
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
