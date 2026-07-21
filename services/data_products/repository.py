from __future__ import annotations

from typing import Protocol, Sequence

from packages.domain_model.data_product import DataProduct


class ProductVersionConflict(RuntimeError):
    pass


class DataProductRepository(Protocol):
    def create(self, product: DataProduct) -> DataProduct: ...
    def get(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None: ...
    def list(
        self, tenant_id: str, environment: str, *, limit: int, cursor: str | None = None
    ) -> Sequence[DataProduct]: ...
    def update(self, product: DataProduct, *, expected_etag: str) -> DataProduct: ...
    def append_revision(self, product: DataProduct, *, actor: str) -> None: ...
