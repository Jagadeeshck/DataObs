"""Scoped lifecycle idempotency records; raw client keys are never persisted."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import Field

from packages.domain_model.base import DomainModel


class IdempotencyConflict(RuntimeError):
    pass


class IdempotencyPending(RuntimeError):
    pass


class DataProductIdempotencyRecord(DomainModel):
    tenant_id: str
    environment: str
    resource_type: Literal["data_product"] = "data_product"
    resource_id: str
    action: str
    idempotency_key_hash: str
    request_fingerprint: str
    operation_id: str | None = None
    state: Literal["pending", "completed", "failed", "superseded"] = "pending"
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    result_revision: int | None = Field(default=None, ge=1)
    result_etag: str | None = None
    error_code: str | None = None
    expires_at: datetime
    schema_version: str = "v1"


def hash_key(key: str) -> str:
    if not key or len(key) > 512:
        raise ValueError("Idempotency-Key is required and must not exceed 512 characters")
    return hashlib.sha256(key.encode()).hexdigest()


def scoped_record_id(tenant_id: str, environment: str, product_id: str, key: str) -> str:
    canonical = "\x1f".join((tenant_id, environment, "data_product", product_id, hash_key(key)))
    return hashlib.sha256(canonical.encode()).hexdigest()


def request_fingerprint(
    *,
    tenant_id: str,
    environment: str,
    product_id: str,
    action: str,
    body: Any,
    actor: str,
    reason: str,
    expected_etag: str | None,
) -> str:
    """Bind actor because a replay must preserve the original audit principal."""
    value = {
        "action": action,
        "actor": actor,
        "body": body,
        "environment": environment,
        "expected_etag": expected_etag,
        "product_id": product_id,
        "reason": reason,
        "tenant_id": tenant_id,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def new_record(
    *,
    tenant_id: str,
    environment: str,
    product_id: str,
    action: str,
    key: str,
    fingerprint: str,
    retention_days: int = 30,
) -> DataProductIdempotencyRecord:
    now = datetime.now(timezone.utc)
    return DataProductIdempotencyRecord(
        tenant_id=tenant_id,
        environment=environment,
        resource_id=product_id,
        action=action,
        idempotency_key_hash=hash_key(key),
        request_fingerprint=fingerprint,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(days=retention_days),
    )
