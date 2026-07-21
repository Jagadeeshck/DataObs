"""OCC guarded declared-dependency replacement."""

from __future__ import annotations

from hashlib import sha256
from typing import Sequence

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductDependencyPage, DataProductDependencyProjection
from services.data_products.dependencies import build_adjacency, reject_cycles
from services.data_products.repository import DataProductRepository


class DataProductDependencyService:
    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def replace_declared_dependencies(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        upstream_ids: Sequence[str],
        *,
        expected_etag: str,
        actor: str,
        reason: str,
        idempotency_key: str,
    ) -> DataProductDependencyPage:
        product = self.repository.get_product(tenant_id, environment, product_id)
        if product is None:
            raise KeyError(product_id)
        if product.etag != expected_etag:
            raise ValueError("stale data product ETag")
        if not actor.strip() or not reason.strip() or not idempotency_key.strip():
            raise ValueError("actor, reason, and idempotency key are required")
        scoped = []
        for upstream_id in sorted(set(upstream_ids)):
            upstream = self.repository.get_product(tenant_id, environment, upstream_id)
            if upstream is None or upstream.lifecycle_state == "archived":
                raise KeyError(upstream_id)
            scoped.append(upstream_id)
        existing = self.repository.list_dependencies(tenant_id, environment, product_id, limit=200).items
        graph = build_adjacency(
            [(product_id, value) for value in scoped]
            + [(e.product_id, e.upstream_product_id) for e in existing if not e.removed and e.product_id != product_id]
        )
        reject_cycles(graph)
        now = utc_now()
        version = sha256("\0".join(scoped).encode()).hexdigest()
        edges = [
            DataProductDependencyProjection(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                upstream_product_id=value,
                product_revision=product.revision + 1,
                graph_version=version,
                observed_at=now,
            )
            for value in scoped
        ]
        return self.repository.save_dependencies(tenant_id, environment, product_id, edges)
