from __future__ import annotations

from packages.domain_model.data_product import DataProduct, DataProductRevisionEvent
from services.data_products.events import ProductConsistencyError
from services.data_products.idempotency import DataProductIdempotencyRecord, IdempotencyConflict
from services.data_products.repository import ProductVersionConflict


class MemoryDataProductRepository:
    """Deterministic test repository; production composition must use Elasticsearch."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str, str], DataProduct] = {}
        self.revisions: dict[tuple[str, str, str, int], tuple[DataProduct, str, str]] = {}
        self.operations: dict[str, tuple[DataProductRevisionEvent, DataProduct]] = {}
        self.idempotency: dict[str, DataProductIdempotencyRecord] = {}

    def reserve_idempotency(self, record_id: str, record: DataProductIdempotencyRecord) -> DataProductIdempotencyRecord:
        existing = self.idempotency.get(record_id)
        if existing:
            if existing.request_fingerprint != record.request_fingerprint:
                raise IdempotencyConflict("idempotency_conflict")
            return existing.model_copy(deep=True)
        self.idempotency[record_id] = record.model_copy(deep=True)
        return record

    def complete_idempotency(self, record_id: str, *, operation_id: str, revision: int, etag: str) -> None:
        from packages.domain_model.base import utc_now

        record = self.idempotency[record_id]
        now = utc_now()
        self.idempotency[record_id] = record.model_copy(
            update={
                "operation_id": operation_id,
                "state": "completed",
                "result_revision": revision,
                "result_etag": etag,
                "completed_at": now,
                "updated_at": now,
            }
        )

    def get_idempotency(self, record_id: str):
        value = self.idempotency.get(record_id)
        return value.model_copy(deep=True) if value else None

    def _terminal_idempotency(self, record_id: str, state: str, error_code: str | None = None) -> None:
        from packages.domain_model.base import utc_now

        record = self.idempotency[record_id]
        if record.state == "completed":
            return
        now = utc_now()
        self.idempotency[record_id] = record.model_copy(
            update={"state": state, "error_code": error_code, "updated_at": now}
        )

    def fail_idempotency(self, record_id: str, *, error_code: str) -> None:
        self._terminal_idempotency(record_id, "failed", error_code)

    def supersede_idempotency(self, record_id: str, *, error_code: str = "newer_revision") -> None:
        self._terminal_idempotency(record_id, "superseded", error_code)

    def list_expired_idempotency(self, tenant_id: str, environment: str, *, now, limit: int = 100):
        return [
            value.model_copy(deep=True)
            for value in sorted(self.idempotency.values(), key=lambda item: (item.expires_at, item.resource_id))
            if (value.tenant_id, value.environment) == (tenant_id, environment) and value.expires_at <= now
        ][:limit]

    def get_product_revision(self, tenant_id: str, environment: str, product_id: str, revision: int):
        value = self.revisions.get((tenant_id, environment, product_id, revision))
        return value[0].model_copy(deep=True) if value else None

    def get_operation(self, tenant_id: str, environment: str, operation_id: str):
        found = self.operations.get(operation_id)
        if found and (found[0].tenant_id, found[0].environment) == (tenant_id, environment):
            return found[0].model_copy(deep=True)
        return None

    def list_pending_operations(
        self, tenant_id: str, environment: str, *, product_id=None, limit=100, include_applied=False
    ):
        values = [
            event
            for event, _ in self.operations.values()
            if (event.tenant_id, event.environment) == (tenant_id, environment)
            and (product_id is None or event.product_id == product_id)
            and (include_applied or event.outcome == "pending")
        ]
        return [
            value.model_copy(deep=True)
            for value in sorted(values, key=lambda x: (x.occurred_at, x.operation_id))[:limit]
        ]

    def list_revisions(self, tenant_id: str, environment: str, product_id: str, *, limit=100, search_after=None):
        values = [
            event
            for event, _ in self.operations.values()
            if (event.tenant_id, event.environment, event.product_id) == (tenant_id, environment, product_id)
        ]
        values.sort(key=lambda x: (x.revision, x.operation_id), reverse=True)
        if search_after:
            values = [v for v in values if (v.revision, v.operation_id) < tuple(search_after)]
        return [v.model_copy(deep=True) for v in values[:limit]]

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
