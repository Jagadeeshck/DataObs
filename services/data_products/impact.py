"""Bounded metadata-only Data Product impact projection."""

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductImpactSummary
from services.data_products.repository import DataProductRepository


class DataProductImpactService:
    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def summarize(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int = 200
    ) -> DataProductImpactSummary:
        if not 1 <= limit <= 1000:
            raise ValueError("impact limit outside bounds")
        product = self.repository.get_product(tenant_id, environment, product_id)
        if product is None:
            raise KeyError(product_id)
        members = self.repository.list_memberships(tenant_id, environment, product_id, limit=limit)
        dependencies = self.repository.list_dependencies(tenant_id, environment, product_id, limit=limit)
        missing = [name for name in ("lineage", "pathways")]
        return DataProductImpactSummary(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            outputs=[o.entity_id for o in product.outputs[:limit]],
            active_members=[m.entity_id for m in members.items if m.state == "active"],
            direct_upstream_products=[e.upstream_product_id for e in dependencies.items if not e.removed],
            truncated=members.has_more or dependencies.has_more,
            missing_evidence=missing,
            source_coverage=0.5,
            data_status="partial",
            observed_at=utc_now(),
        )
