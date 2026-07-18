from __future__ import annotations

from typing import Any, Dict, List

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError as ESConflictError
from elasticsearch.exceptions import NotFoundError as ESNotFoundError

from packages.elastic_store.registry import status as migration_status

from .repository import ConflictError, NotFoundError, now

BUCKET_ALIASES = {
    "tenants": "dataobs-tenants-v1-write",
    "sources": "dataobs-sources-v1-write",
    "integrations": "dataobs-integrations-v1-write",
    "collectors": "dataobs-collectors-v1-write",
    "scanners": "dataobs-scanners-v1-write",
    "policies": "dataobs-scan-policies-v1-write",
    "tasks": "dataobs-tasks-v1-write",
    "leases": "dataobs-task-leases-v1-write",
    "idempotency": "dataobs-idempotency-v1-write",
    "assets": "dataobs-assets-v1-write",
    "schema_current": "dataobs-schema-current-v1-write",
    "freshness_current": "dataobs-freshness-current-v1-write",
    "profile_current": "dataobs-profile-current-v1-write",
    "quality_current": "dataobs-quality-current-v1-write",
}
EVENT_STREAMS = {
    "audit": "logs-dataobs.audit-default",
    "schema_snapshot": "logs-dataobs.schema_snapshot-default",
    "schema_change": "logs-dataobs.schema_change-default",
    "scan_execution": "logs-dataobs.scan_execution-default",
    "scan_error": "logs-dataobs.scan_error-default",
    "quality_result": "logs-dataobs.quality_result-default",
    "database_inventory": "logs-dataobs.database_inventory-default",
    "freshness": "metrics-dataobs.freshness-default",
    "table_profile": "metrics-dataobs.table_profile-default",
    "column_profile": "metrics-dataobs.column_profile-default",
    "scanner_health": "metrics-dataobs.scanner_health-default",
}


class ElasticsearchCollectionRepository:
    def __init__(self, es: Elasticsearch):
        self.es = es

    def _index(self, bucket: str) -> str:
        return BUCKET_ALIASES[bucket]

    def readiness(self):
        st = migration_status(self.es)
        if not st.get("ready"):
            raise RuntimeError(f"Elasticsearch migrations are not ready: {st}")
        return {"ready": True, "backend": "elasticsearch", "migration_status": st}

    def upsert(
        self,
        bucket: str,
        doc: Dict[str, Any],
        *,
        expected_version: int | None = None,
        if_seq_no: int | None = None,
        if_primary_term: int | None = None,
    ):
        body = {k: v for k, v in {**doc, "updated_at": now()}.items() if not k.startswith("_")}
        kwargs: Dict[str, Any] = {}
        if expected_version is not None and (if_seq_no is None or if_primary_term is None):
            current = self.get(bucket, doc["id"], doc.get("tenant_id"))
            if not current or current.get("_seq_no") is None or current.get("_primary_term") is None:
                raise ConflictError(f"missing concurrency token for {bucket}/{doc['id']}")
            if_seq_no = current.get("_seq_no")
            if_primary_term = current.get("_primary_term")
        if if_seq_no is not None or if_primary_term is not None:
            if if_seq_no is None or if_primary_term is None:
                raise ConflictError("both if_seq_no and if_primary_term are required")
            kwargs["if_seq_no"] = if_seq_no
            kwargs["if_primary_term"] = if_primary_term
        try:
            resp = self.es.index(index=self._index(bucket), id=doc["id"], document=body, refresh="wait_for", **kwargs)
        except ESConflictError as exc:
            raise ConflictError(str(exc)) from exc
        return {
            **body,
            "_version": resp.get("_version"),
            "_seq_no": resp.get("_seq_no"),
            "_primary_term": resp.get("_primary_term"),
        }

    def get(self, bucket: str, id: str, tenant_id: str | None = None):
        try:
            hit = self.es.get(index=self._index(bucket), id=id)
        except ESNotFoundError:
            return None
        doc = hit["_source"]
        if tenant_id is not None and doc.get("tenant_id") != tenant_id:
            return None
        return {
            **doc,
            "_version": hit.get("_version"),
            "_seq_no": hit.get("_seq_no"),
            "_primary_term": hit.get("_primary_term"),
        }

    def list(self, bucket: str, tenant_id: str, **filters: Any) -> List[Dict[str, Any]]:
        must = [{"term": {"tenant_id": tenant_id}}] + [{"term": {k: v}} for k, v in filters.items() if v is not None]
        resp = self.es.search(
            index=self._index(bucket).replace("-write", "-read"),
            query={"bool": {"filter": must}},
            sort=[{"updated_at": "asc"}, {"id": "asc"}],
            size=1000,
        )
        return [
            {
                **h["_source"],
                "_version": h.get("_version"),
                "_seq_no": h.get("_seq_no"),
                "_primary_term": h.get("_primary_term"),
            }
            for h in resp["hits"]["hits"]
        ]

    def delete(self, bucket: str, id: str, tenant_id: str, *, expected_version: int | None = None):
        doc = self.get(bucket, id, tenant_id)
        if not doc:
            raise NotFoundError(f"{bucket}/{id} not found")
        self.es.delete(index=self._index(bucket), id=id, refresh="wait_for")

    def event(self, event_type: str, doc: Dict[str, Any]):
        rec = {"@timestamp": now(), "event_type": event_type, **doc}
        self.es.index(index=EVENT_STREAMS.get(event_type, "logs-dataobs.scan_execution-default"), document=rec)
        return rec

    def audit_event(self, action: str, tenant_id: str, correlation_id: str | None, resource_id: str):
        return self.event(
            "audit",
            {"action": action, "tenant_id": tenant_id, "correlation_id": correlation_id, "resource_id": resource_id},
        )
