from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from elasticsearch import Elasticsearch

from .manifest import BASE_PROPERTIES, DATA_STREAMS, MIGRATION_STATE_INDEX, MUTABLE_INDICES, migrations


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
        | {"id": {"type": "keyword"}, "name": {"type": "keyword"}, "document": {"type": "flattened"}},
    }


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
    for index in MUTABLE_INDICES:
        if not es.indices.exists(index=index):
            es.indices.create(index=index, mappings=_mapping())
        for suffix in ("read", "write"):
            alias = f"{index}-{suffix}"
            if not es.indices.exists_alias(index=index, name=alias):
                es.indices.put_alias(index=index, name=alias)
    for pattern in DATA_STREAMS:
        name = f"dataobs-{pattern.replace('*','template').replace('.','-')}"
        es.indices.put_index_template(
            name=name,
            index_patterns=[pattern],
            data_stream={},
            template={"mappings": {"dynamic": "strict", "properties": BASE_PROPERTIES}},
        )
    out = []
    for m in migrations():
        doc = {
            "migration_id": m.migration_id,
            "schema_version": m.schema_version,
            "checksum": m.checksum,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "status": "applied",
        }
        es.index(index=MIGRATION_STATE_INDEX, id=m.migration_id, document=doc)
        out.append(doc)
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
