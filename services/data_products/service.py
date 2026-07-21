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

    def create(self, product: DataProduct, *, actor: str, reason: str = "created") -> DataProduct:
        if not product.owner.team or not product.criticality:
            raise ValueError("owner and criticality are required")
        product.revision = 1
        self.validate_dependencies(product)
        product.etag = product_etag(product)
        created = self.repository.create(product)
        self.repository.append_revision(created, actor=actor, reason=reason)
        return created

    def update(self, product: DataProduct, *, if_match: str | None, actor: str, reason: str = "updated") -> DataProduct:
        if not if_match:
            raise ProductVersionConflict("If-Match is required")
        current = self.repository.get(product.tenant_id, product.environment, product.id)
        if current is None:
            raise KeyError(product.id)
        if current.etag != if_match:
            raise ProductVersionConflict("stale data product ETag")
        product.revision = current.revision + 1
        self.validate_dependencies(product)
        product.updated_at = datetime.now(timezone.utc)
        product.etag = product_etag(product)
        saved = self.repository.update(product, expected_etag=if_match)
        self.repository.append_revision(saved, actor=actor, reason=reason)
        return saved

    def validate_dependencies(self, product: DataProduct, *, max_depth: int = 32, max_nodes: int = 1000) -> None:
        """Validate the complete scoped graph with deterministic, bounded traversal."""
        graph: dict[str, list[str]] = {product.id: sorted({d.upstream_product_id for d in product.dependencies})}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str, depth: int) -> None:
            if depth > max_depth:
                raise ValueError("data product dependency depth limit exceeded")
            if node in visiting:
                raise ValueError("data product dependency cycle")
            if node in visited:
                return
            if len(visited) + len(visiting) >= max_nodes:
                raise ValueError("data product dependency node limit exceeded")
            visiting.add(node)
            if node not in graph:
                candidate = self.repository.get(product.tenant_id, product.environment, node)
                if candidate is None:
                    raise ValueError(f"unknown or cross-tenant dependency: {node}")
                graph[node] = sorted({d.upstream_product_id for d in candidate.dependencies})
            for nxt in graph[node]:
                visit(nxt, depth + 1)
            visiting.remove(node)
            visited.add(node)

        visit(product.id, 0)
