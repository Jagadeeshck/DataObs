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

    def get(self, tenant_id: str, environment: str, product_id: str) -> DataProduct:
        product = self.repository.get(tenant_id, environment, product_id)
        if product is None:
            raise KeyError(product_id)
        return product

    def list(self, tenant_id: str, environment: str, *, limit: int = 50, cursor: str | None = None):
        return self.repository.list(tenant_id, environment, limit=limit, cursor=cursor)

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

    def _transition(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        target: str,
        *,
        if_match: str | None,
        actor: str,
        reason: str,
    ) -> DataProduct:
        current = self.get(tenant_id, environment, product_id)
        allowed = {
            "draft": {"active", "archived"},
            "active": {"deprecated", "archived"},
            "deprecated": {"archived"},
            "archived": set(),
        }
        if target not in allowed[current.lifecycle_state]:
            raise ValueError(f"invalid lifecycle transition: {current.lifecycle_state} -> {target}")
        if target == "active" and (not current.owner.team or not current.criticality or not current.outputs):
            raise ValueError("activation requires owner, criticality, and at least one output")
        changed = current.model_copy(deep=True)
        changed.lifecycle_state = target
        return self.update(changed, if_match=if_match, actor=actor, reason=reason)

    def activate(
        self, tenant_id: str, environment: str, product_id: str, *, if_match: str | None, actor: str, reason: str
    ) -> DataProduct:
        return self._transition(
            tenant_id, environment, product_id, "active", if_match=if_match, actor=actor, reason=reason
        )

    def deprecate(
        self, tenant_id: str, environment: str, product_id: str, *, if_match: str | None, actor: str, reason: str
    ) -> DataProduct:
        return self._transition(
            tenant_id, environment, product_id, "deprecated", if_match=if_match, actor=actor, reason=reason
        )

    def archive(
        self, tenant_id: str, environment: str, product_id: str, *, if_match: str | None, actor: str, reason: str
    ) -> DataProduct:
        return self._transition(
            tenant_id, environment, product_id, "archived", if_match=if_match, actor=actor, reason=reason
        )

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
