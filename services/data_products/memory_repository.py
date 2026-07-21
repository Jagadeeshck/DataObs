from __future__ import annotations

from packages.domain_model.data_product import DataProduct
from services.data_products.repository import ProductVersionConflict


class MemoryDataProductRepository:
    """Deterministic test repository; production composition must use Elasticsearch."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str, str], DataProduct] = {}
        self.revisions: list[DataProduct] = []

    def create(self, product: DataProduct) -> DataProduct:
        key = (product.tenant_id, product.environment, product.id)
        if key in self.items:
            raise ProductVersionConflict("data product exists")
        self.items[key] = product.model_copy(deep=True)
        return product

    def get(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None:
        item = self.items.get((tenant_id, environment, product_id))
        return item.model_copy(deep=True) if item else None

    def list(self, tenant_id: str, environment: str, *, limit: int, cursor: str | None = None) -> list[DataProduct]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        values = sorted(
            (p for (t, e, _), p in self.items.items() if (t, e) == (tenant_id, environment)), key=lambda p: p.id
        )
        if cursor:
            values = [p for p in values if p.id > cursor]
        return [p.model_copy(deep=True) for p in values[:limit]]

    def update(self, product: DataProduct, *, expected_etag: str) -> DataProduct:
        key = (product.tenant_id, product.environment, product.id)
        current = self.items.get(key)
        if current is None:
            raise KeyError(product.id)
        if current.etag != expected_etag:
            raise ProductVersionConflict("stale data product ETag")
        self.items[key] = product.model_copy(deep=True)
        return product

    def append_revision(self, product: DataProduct, *, actor: str) -> None:
        del actor
        self.revisions.append(product.model_copy(deep=True))
