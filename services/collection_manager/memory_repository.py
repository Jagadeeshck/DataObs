from __future__ import annotations

from typing import Any, Dict, List

from .repository import ConflictError, NotFoundError, now


class InMemoryCollectionRepository:
    """Local/test-only repository. Production must configure Elasticsearch."""

    def __init__(self):
        self.tenants = {}
        self.sources = {}
        self.integrations = {}
        self.collectors = {}
        self.scanners = {}
        self.policies = {}
        self.tasks = {}
        self.leases = {}
        self.idempotency = {}
        self.assets = {}
        self.schema_current = {}
        self.freshness_current = {}
        self.profile_current = {}
        self.quality_current = {}
        self.events = []
        self.audit = []
        self.results = {}

    def _bucket(self, bucket: str):
        return getattr(self, bucket)

    def upsert(self, bucket: str, doc: Dict[str, Any], *, expected_version: int | None = None):
        store = self._bucket(bucket)
        current = store.get(doc["id"])
        if expected_version is not None and (not current or current.get("_version") != expected_version):
            raise ConflictError(f"version conflict for {bucket}/{doc['id']}")
        version = (current or {}).get("_version", 0) + 1
        stored = {**doc, "_version": version, "updated_at": now()}
        store[doc["id"]] = stored
        return stored

    def get(self, bucket: str, id: str, tenant_id: str | None = None):
        doc = self._bucket(bucket).get(id)
        if doc and (tenant_id is None or doc.get("tenant_id") == tenant_id):
            return doc
        return None

    def list(self, bucket: str, tenant_id: str, **filters: Any):
        out = []
        for d in self._bucket(bucket).values():
            if d.get("tenant_id") == tenant_id and all(v is None or d.get(k) == v for k, v in filters.items()):
                out.append(d)
        return sorted(out, key=lambda d: (d.get("updated_at", ""), d.get("id", "")))

    def delete(self, bucket: str, id: str, tenant_id: str, *, expected_version: int | None = None):
        doc = self.get(bucket, id, tenant_id)
        if not doc:
            raise NotFoundError(f"{bucket}/{id} not found")
        if expected_version is not None and doc.get("_version") != expected_version:
            raise ConflictError(f"version conflict for {bucket}/{id}")
        del self._bucket(bucket)[id]

    def event(self, event_type: str, doc: Dict[str, Any]):
        rec = {"@timestamp": now(), "event_type": event_type, **doc}
        self.events.append(rec)
        return rec

    def audit_event(self, action: str, tenant_id: str, correlation_id: str | None, resource_id: str):
        rec = {
            "@timestamp": now(),
            "action": action,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "resource_id": resource_id,
        }
        self.audit.append(rec)
        return rec

    def readiness(self):
        return {"ready": True, "backend": "memory", "production": False}
