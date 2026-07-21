from __future__ import annotations

from packages.domain_model.data_product import DataProduct, DataProductRevisionEvent
from services.data_products.events import ProductConsistencyError
from services.data_products.repository import ProductVersionConflict


class MemoryDataProductRepository:
    """Deterministic test repository; production composition must use Elasticsearch."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str, str], DataProduct] = {}
        self.revisions: dict[tuple[str, str, str, int], tuple[DataProduct, str, str]] = {}
        self.operations: dict[str, tuple[DataProductRevisionEvent, DataProduct]] = {}

    def begin_operation(self, event: DataProductRevisionEvent, product: DataProduct) -> DataProductRevisionEvent:
        existing = self.operations.get(event.operation_id)
        if existing:
            if existing[0].definition_checksum != event.definition_checksum:
                raise ProductConsistencyError("divergent operation replay")
            return existing[0].model_copy(deep=True)
        revision_key = (event.tenant_id, event.environment, event.product_id, event.revision)
        for saved_event, _ in self.operations.values():
            if (
                saved_event.tenant_id,
                saved_event.environment,
                saved_event.product_id,
                saved_event.revision,
            ) == revision_key and saved_event.definition_checksum != event.definition_checksum:
                raise ProductConsistencyError("divergent same-revision checksum")
        self.operations[event.operation_id] = (event.model_copy(deep=True), product.model_copy(deep=True))
        return event

    def finish_operation(self, event: DataProductRevisionEvent) -> None:
        existing = self.operations.get(event.operation_id)
        if not existing or existing[0].definition_checksum != event.definition_checksum:
            raise ProductConsistencyError("operation outcome has no matching pending operation")
        self.operations[event.operation_id] = (event.model_copy(deep=True), existing[1])
        product = existing[1]
        self.revisions[(event.tenant_id, event.environment, event.product_id, event.revision)] = (
            product.model_copy(deep=True),
            event.actor,
            event.reason,
        )

    def create_product(self, product: DataProduct) -> DataProduct:
        key = (product.tenant_id, product.environment, product.id)
        if key in self.items:
            raise ProductVersionConflict("data product exists")
        self.items[key] = product.model_copy(deep=True)
        return product

    def get_product(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None:
        item = self.items.get((tenant_id, environment, product_id))
        return item.model_copy(deep=True) if item else None

    def list_products(
        self, tenant_id: str, environment: str, *, limit: int, cursor: str | None = None
    ) -> list[DataProduct]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        values = sorted(
            (p for (t, e, _), p in self.items.items() if (t, e) == (tenant_id, environment)), key=lambda p: p.id
        )
        if cursor:
            values = [p for p in values if p.id > cursor]
        return [p.model_copy(deep=True) for p in values[:limit]]

    def update_product(self, product: DataProduct, *, expected_etag: str) -> DataProduct:
        key = (product.tenant_id, product.environment, product.id)
        current = self.items.get(key)
        if current is None:
            raise KeyError(product.id)
        if current.etag != expected_etag:
            raise ProductVersionConflict("stale data product ETag")
        self.items[key] = product.model_copy(deep=True)
        return product

    def append_revision(self, product: DataProduct, *, actor: str, reason: str) -> None:
        key = (product.tenant_id, product.environment, product.id, product.revision)
        existing = self.revisions.get(key)
        event = (product.model_copy(deep=True), actor, reason)
        if existing:
            if existing[0].model_dump(mode="json") == event[0].model_dump(mode="json") and existing[1:] == event[1:]:
                return
            raise ProductVersionConflict("divergent data product revision")
        self.revisions[key] = event
