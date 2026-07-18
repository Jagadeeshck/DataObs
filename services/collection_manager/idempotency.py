from __future__ import annotations

from .repository import ConflictError


def record_once(repo, tenant_id, key, response):
    existing = repo.get("idempotency", key, tenant_id)
    if existing:
        return existing.get("response")
    try:
        repo.upsert("idempotency", {"id": key, "tenant_id": tenant_id, "response": response})
    except ConflictError:
        return repo.get("idempotency", key, tenant_id).get("response")
    return response
