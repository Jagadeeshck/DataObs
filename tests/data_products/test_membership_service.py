"""Shared-coordinator contracts for synchronous membership mutations."""

from packages.domain_model.data_product import DataProduct, DataProductCriticality, DataProductOwner
from services.data_products.membership_service import DataProductMembershipService
from services.data_products.memory_repository import MemoryDataProductRepository


def test_manual_success_finishes_all_generic_stores() -> None:
    repository = MemoryDataProductRepository()
    repository.create_product(
        DataProduct(
            id="orders",
            tenant_id="tenant",
            environment="prod",
            name="Orders",
            domain="sales",
            owner=DataProductOwner(team="data"),
            criticality=DataProductCriticality.HIGH,
            etag="v1",
        )
    )
    result = DataProductMembershipService(repository).add_manual_member(
        "tenant",
        "prod",
        "orders",
        entity_id="asset",
        entity_type="table",
        actor="alice",
        reason="owned",
        idempotency_key="request-1",
    )
    state = repository.get_operation_state("tenant", "prod", result.operation_id)
    assert state is not None and state.status == "applied" and state.result_reference
    assert repository.load_operation_result("tenant", "prod", "orders", result.operation_id)
    assert any(
        event.outcome == "applied" for event in repository.get_operation_history("tenant", "prod", result.operation_id)
    )
    assert next(iter(repository.idempotency.values())).state == "completed"
