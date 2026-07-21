from packages.domain_model.data_product import (
    DataProduct,
    DataProductCriticality,
    DataProductOwner,
)
from services.data_products.membership_service import DataProductMembershipService
from services.data_products.memory_repository import MemoryDataProductRepository


def test_manual_membership_is_event_first_and_never_persists_raw_key():
    repository = MemoryDataProductRepository()
    repository.create_product(
        DataProduct(
            id="orders",
            tenant_id="tenant-a",
            environment="prod",
            etag="v1",
            name="Orders",
            domain="commerce",
            criticality=DataProductCriticality.HIGH,
            owner=DataProductOwner(team="data"),
        )
    )
    result = DataProductMembershipService(repository).add_manual_member(
        "tenant-a",
        "prod",
        "orders",
        entity_id="orders.table",
        entity_type="asset",
        actor="operator",
        reason="declared output",
        idempotency_key="raw-secret-key",
    )
    decisions = repository.list_membership_decisions("tenant-a", "prod", "orders")
    assert result.state == "active"
    assert {decision.outcome for decision in decisions.items} == {"pending", "applied"}
    assert "raw-secret-key" not in repr(repository.idempotency)
    assert next(iter(repository.idempotency.values())).state == "completed"
