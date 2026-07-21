from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.data_product import DataProduct, DataProductCriticality, DataProductOwner
from packages.elastic_store.manifest import (
    DATA_PRODUCT_EVENT_PROPERTIES,
    DATA_PRODUCT_PROPERTIES,
    migrations,
)
from services.data_products.events import ProductConsistencyError
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.service import DataProductService
from services.data_products.slo_evaluator import evaluate_slo
from tests.data_products.test_completion import slo


def _product(tenant: str = "tenant-a") -> DataProduct:
    now = datetime.now(timezone.utc)
    return DataProduct(
        id="orders",
        tenant_id=tenant,
        environment="prod",
        criticality=DataProductCriticality.HIGH,
        domain="sales",
        name="Orders",
        owner=DataProductOwner(team="data"),
        etag="",
        created_at=now,
        updated_at=now,
    )


def test_0015_is_forward_only_and_writer_mappings_are_explicit():
    migration = migrations()[-2]
    assert migration.migration_id == "0015_data_product_360_productization"
    assert migration.dependencies == ["0014_data_product_360_completion"]
    assert not migration.operations.get("mutable_indices")
    assert {"id", "owner", "outputs", "revision", "etag"} <= DATA_PRODUCT_PROPERTIES.keys()
    assert {"operation_id", "definition_checksum", "action", "outcome"} <= DATA_PRODUCT_EVENT_PROPERTIES.keys()


def test_pending_operation_is_durable_before_current_state():
    class RecordingRepository(MemoryDataProductRepository):
        def create(self, product):
            assert len(self.operations) == 1
            assert next(iter(self.operations.values()))[0].outcome == "pending"
            return super().create(product)

    repository = RecordingRepository()
    DataProductService(repository).create(_product(), actor="alice", idempotency_key="request-1")
    assert next(iter(repository.operations.values()))[0].outcome == "applied"


def test_divergent_same_revision_is_rejected_before_mutation():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    value = _product()
    service.create(value, actor="alice", idempotency_key="request-1")
    repository.items.clear()  # simulate a crash after pending/outcome evidence
    with pytest.raises(ProductConsistencyError, match="divergent"):
        service.create(value.model_copy(update={"name": "Poisoned"}), actor="mallory", idempotency_key="request-1")


def test_slo_evaluation_identity_is_scoped_and_corrected_evidence_is_new():
    now = datetime.now(timezone.utc)
    start, end = now - timedelta(days=1), now - timedelta(seconds=1)
    definition = slo()

    def evaluate(current, refs):
        return evaluate_slo(
            current,
            window_start=start,
            window_end=end,
            actual_value=1,
            denominator=1,
            evidence_refs=refs,
            now=now,
        )

    original = evaluate(definition, ["evaluation-1"])
    assert evaluate(definition, ["evaluation-1"]).id == original.id
    assert evaluate(definition.model_copy(update={"tenant_id": "other"}), ["evaluation-1"]).id != original.id
    assert evaluate(definition.model_copy(update={"product_id": "other"}), ["evaluation-1"]).id != original.id
    assert evaluate(definition, ["corrected-evaluation"]).id != original.id
    assert (original.tenant_id, original.environment, original.product_id) == ("t", "prod", "p")
