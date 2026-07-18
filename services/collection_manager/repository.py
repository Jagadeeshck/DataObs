from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def now():
    return datetime.now(timezone.utc).isoformat()


class InMemoryCollectionRepository:
    def __init__(self):
        self.tenants = {}
        self.sources = {}
        self.integrations = {}
        self.collectors = {}
        self.scanners = {}
        self.policies = {}
        self.tasks = {}
        self.assets = {}
        self.events = []
        self.audit = []
        self.results = {}

    def upsert(self, bucket: str, doc: Dict[str, Any]):
        getattr(self, bucket)[doc["id"]] = doc
        return doc

    def get(self, bucket: str, id: str):
        return getattr(self, bucket).get(id)

    def list(self, bucket: str, tenant_id: str):
        return [d for d in getattr(self, bucket).values() if d.get("tenant_id") == tenant_id]

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
