"""Lifecycle durable-plan ordering contracts."""

from packages.domain_model.data_product import DataProductOutput
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.service import DataProductService
from tests.data_products.test_service import product


class OrderingRepository(MemoryDataProductRepository):
    def update_product(self, value, *, expected_etag):
        if value.lifecycle_state != "draft":
            states = [state for state in self.operation_states.values() if state.operation_kind == "product_lifecycle"]
            assert states and states[-1].status == "pending"
            plan = self.load_operation_plan(value.tenant_id, value.environment, value.id, states[-1].operation_id)
            assert plan is not None and plan.payload["target_product"]["lifecycle_state"] == value.lifecycle_state
        return super().update_product(value, expected_etag=expected_etag)


def test_lifecycle_plan_and_state_precede_projection_update() -> None:
    repository = OrderingRepository()
    service = DataProductService(repository)
    draft = product("orders")
    draft.outputs = [DataProductOutput(entity_id="orders", entity_type="asset")]
    created = service.create(draft, actor="seed")
    active = service.activate(
        "tenant-a",
        "default",
        "orders",
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="activate-1",
    )
    state = next(state for state in repository.operation_states.values() if state.operation_kind == "product_lifecycle")
    assert active.lifecycle_state == "active" and state.status == "applied"
