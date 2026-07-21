from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from packages.domain_model.data_product import DataProduct
from services.data_products.repository import DataProductRepository, ProductVersionConflict


def product_etag(product: DataProduct) -> str:
    return '"' + sha256(product.model_dump_json(exclude={"etag", "updated_at"}).encode()).hexdigest() + '"'


class DataProductService:
    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def create(self, product: DataProduct, *, actor: str) -> DataProduct:
        if not product.owner.team or not product.criticality:
            raise ValueError("owner and criticality are required")
        product.etag = product_etag(product)
        created = self.repository.create(product)
        self.repository.append_revision(created, actor=actor)
        return created

    def update(self, product: DataProduct, *, if_match: str | None, actor: str) -> DataProduct:
        if not if_match:
            raise ProductVersionConflict("If-Match is required")
        current = self.repository.get(product.tenant_id, product.environment, product.id)
        if current is None:
            raise KeyError(product.id)
        if current.etag != if_match:
            raise ProductVersionConflict("stale data product ETag")
        product.updated_at = datetime.now(timezone.utc)
        product.etag = product_etag(product)
        saved = self.repository.update(product, expected_etag=if_match)
        self.repository.append_revision(saved, actor=actor)
        return saved

    def validate_dependencies(self, product: DataProduct) -> None:
        graph: dict[str, list[str]] = {product.id: [d.upstream_product_id for d in product.dependencies]}
        for upstream in graph[product.id]:
            candidate = self.repository.get(product.tenant_id, product.environment, upstream)
            if candidate is None:
                raise ValueError(f"unknown or cross-tenant dependency: {upstream}")
            graph[upstream] = [d.upstream_product_id for d in candidate.dependencies]
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("data product dependency cycle")
            if node in visited:
                return
            visiting.add(node)
            for nxt in graph.get(node, []):
                visit(nxt)
            visiting.remove(node)
            visited.add(node)

        visit(product.id)
