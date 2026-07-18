from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from packages.domain_model import Asset, Source, Tenant, deterministic_id
from src.core.pillars import Pillar

from .memory_repository import InMemoryCollectionRepository
from .repository import now
from .scanner_tasks import task_id_for

SECRET_KEYS = {"password", "secret", "token", "api_key", "private_key"}


def redact(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in doc.items():
        if k.lower() in SECRET_KEYS:
            continue
        out[k] = redact(v) if isinstance(v, dict) else v
    return out


class CollectionManagerService:
    def __init__(self, repo=None):
        self.repo = repo or InMemoryCollectionRepository()

    def create_tenant(self, payload, correlation_id=None):
        t = Tenant.build(
            payload.get("tenant_id") or payload.get("id"),
            payload["display_name"],
            payload.get("namespace") or payload.get("tenant_id") or payload.get("id"),
            **{k: v for k, v in payload.items() if k not in {"id", "tenant_id", "display_name", "namespace"}},
        ).model_dump(mode="json")
        self.repo.upsert("tenants", t)
        self.repo.audit_event("tenant.create", t["tenant_id"], correlation_id, t["id"])
        return t

    def create_source(self, tenant_id, payload, correlation_id=None):
        safe = redact(payload)
        s = Source.build(
            tenant_id,
            safe.get("environment", "default"),
            safe["source_name"],
            safe["source_type"],
            safe["connector_type"],
            **{
                k: v
                for k, v in safe.items()
                if k not in {"id", "tenant_id", "environment", "source_name", "source_type", "connector_type"}
            },
        ).model_dump(mode="json")
        self.repo.upsert("sources", s)
        self.repo.audit_event("source.create", tenant_id, correlation_id, s["id"])
        return s

    def register(self, bucket, tenant_id, payload, prefix):
        doc = {
            **redact(payload),
            "tenant_id": tenant_id,
            "id": payload.get("id")
            or deterministic_id(
                prefix,
                [
                    tenant_id,
                    payload.get("environment", "default"),
                    payload.get("name")
                    or payload.get(f"{prefix}_identity")
                    or payload.get(f"{prefix}_type")
                    or payload.get("source_id"),
                ],
            ),
            "updated_at": now(),
            "created_at": payload.get("created_at") or now(),
            "schema_version": "v1",
        }
        self.repo.upsert(bucket, doc)
        self.repo.audit_event(f"{prefix}.upsert", tenant_id, doc.get("correlation_id"), doc["id"])
        return doc

    def heartbeat(self, bucket, tenant_id, id, payload):
        doc = self.repo.get(bucket, id)
        if not doc or doc.get("tenant_id") != tenant_id:
            raise KeyError(id)
        doc = {**doc, "health": payload.get("health", "healthy"), "last_heartbeat": now(), "updated_at": now()}
        self.repo.upsert(bucket, doc)
        self.repo.event(f"{bucket}.heartbeat", {"tenant_id": tenant_id, "id": id, **redact(payload)})
        return doc

    def create_policy(self, tenant_id, payload):
        return self.register("policies", tenant_id, payload, "scan_policy")

    def tasks_for_scanner(self, tenant_id, scanner_id):
        scanner = self.repo.get("scanners", scanner_id)
        if not scanner or scanner.get("tenant_id") != tenant_id:
            raise KeyError(scanner_id)
        tasks = []
        for p in self.repo.list("policies", tenant_id):
            if not p.get("enabled", True):
                continue
            tid = task_id_for(p["id"], scanner_id)
            task = self.repo.get("tasks", tid, tenant_id) or self.repo.upsert(
                "tasks",
                {
                    "id": tid,
                    "task_id": tid,
                    "tenant_id": tenant_id,
                    "scanner_id": scanner_id,
                    "policy_id": p["id"],
                    "source_id": p.get("source_id"),
                    "lease_version": 1,
                    "status": "available",
                    "operation": p.get("operation"),
                },
            )
            tasks.append(task)
        return tasks

    def ack_task(self, tenant_id, scanner_id, task_id):
        task = self.repo.get("tasks", task_id, tenant_id)
        if not task or task["scanner_id"] != scanner_id:
            raise KeyError(task_id)
        return self.repo.upsert(
            "tasks",
            {**task, "status": "acknowledged", "acked_at": task.get("acked_at") or now()},
            expected_version=task.get("_version"),
        )

    def submit_result(self, tenant_id, scanner_id, task_id, payload, idem_key=None):
        task = self.repo.get("tasks", task_id, tenant_id)
        if not task or task["scanner_id"] != scanner_id:
            raise KeyError(task_id)
        result_key = idem_key or deterministic_id(
            "result", [tenant_id, scanner_id, task_id, json.dumps(payload, sort_keys=True)]
        )
        existing = self.repo.get("idempotency", result_key, tenant_id)
        if existing:
            return existing.get("response")
        source_id = task.get("source_id") or payload.get("source_id")
        fqn = (
            payload.get("fully_qualified_name")
            or payload.get("asset", {}).get("fully_qualified_name")
            or payload.get("name")
        )
        namespace = payload.get("namespace", "default")
        fingerprint = hashlib.sha256(json.dumps(payload.get("schema", payload), sort_keys=True).encode()).hexdigest()
        asset = Asset.build(
            tenant_id,
            payload.get("environment", "default"),
            namespace,
            fqn,
            payload.get("asset_type", "table"),
            source_id,
            owner_team=payload.get("owner_team"),
            business_service=payload.get("business_service"),
            pillar=Pillar.DATA,
            schema_fingerprint=fingerprint,
            last_observed=now(),
        ).model_dump(mode="json")
        self.repo.event(
            "schema_snapshot",
            {
                "tenant_id": tenant_id,
                "task_id": task_id,
                "source_id": source_id,
                "asset_id": asset["id"],
                "schema_fingerprint": fingerprint,
                "payload": redact(payload),
            },
        )
        self.repo.upsert("assets", asset)
        self.repo.audit_event("scanner.result", tenant_id, payload.get("correlation_id"), asset["id"])
        response = {"status": "accepted", "idempotency_key": result_key, "asset_id": asset["id"], "asset": asset}
        self.repo.upsert("idempotency", {"id": result_key, "tenant_id": tenant_id, "response": response})
        return response
