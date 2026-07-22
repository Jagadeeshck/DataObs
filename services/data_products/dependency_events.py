"""Typed dependency mutation and immutable-operation contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from packages.domain_model.data_product import (
    DataProduct,
    DataProductDependencyProjection,
)


def canonical_upstream_ids(product_id: str, values: Sequence[str], *, maximum: int = 10_000) -> tuple[str, ...]:
    stripped = tuple(value.strip() for value in values)
    if any(not value for value in stripped):
        raise ValueError("upstream product IDs must not be whitespace-only")
    normalized = tuple(sorted(set(stripped)))
    if product_id in normalized:
        raise ValueError("self dependency is not allowed")
    if len(normalized) > maximum:
        raise ValueError("dependency_count_exceeded")
    return normalized


def dependency_request_fingerprint(
    *,
    tenant_id: str,
    environment: str,
    product_id: str,
    upstream_product_ids: Sequence[str],
    actor: str,
    reason: str,
    expected_product_etag: str,
) -> str:
    value = {
        "actor": actor.strip(),
        "environment": environment,
        "expected_product_etag": expected_product_etag,
        "product_id": product_id,
        "reason": reason.strip(),
        "tenant_id": tenant_id,
        "upstream_product_ids": canonical_upstream_ids(product_id, upstream_product_ids),
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class DataProductDependencyReplaceRequest:
    upstream_product_ids: tuple[str, ...]
    actor: str
    reason: str
    expected_product_etag: str


@dataclass(frozen=True)
class DataProductDependencyReadSnapshot:
    dependencies: tuple[DataProductDependencyProjection, ...]
    count: int
    complete: bool
    truncation_reason: str | None = None


@dataclass(frozen=True)
class DataProductDependencyMutationPlan:
    current_product_revision: int
    next_product_revision: int
    expected_product_etag: str
    new_product_etag: str
    before_graph_version: str
    after_graph_version: str
    upserts: tuple[DataProductDependencyProjection, ...]
    tombstones: tuple[DataProductDependencyProjection, ...]
    warnings: tuple[str, ...]
    request_fingerprint: str


@dataclass(frozen=True)
class DataProductDependencyMutationResult:
    product: DataProduct
    dependencies: tuple[DataProductDependencyProjection, ...]
    operation_id: str
    replayed: bool
    warnings: tuple[str, ...]
    removed_count: int
    upserted_count: int
    graph_version: str


@dataclass(frozen=True)
class DataProductDependencyOperation:
    operation_id: str
    tenant_id: str
    environment: str
    product_id: str
    actor: str
    reason: str
    request_fingerprint: str
    idempotency_key_hash: str
    expected_product_revision: int
    expected_product_etag: str
    before_graph_version: str
    after_graph_version: str
    before_checksum: str
    after_checksum: str
    outcome: str
    occurred_at: datetime
    schema_version: str = "v1"


@dataclass(frozen=True)
class DataProductDependencyOperationResult:
    operation: DataProductDependencyOperation
    result_product_revision: int
    result_product_etag: str
    applied_at: datetime
