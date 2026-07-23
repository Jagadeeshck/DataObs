import os

import pytest
from elasticsearch import Elasticsearch

from packages.domain_model.base import utc_now
from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.operation_state import DataProductOperationState
from services.data_products.reconciliation import DataProductOperationService


def test_scoped_operation_id_collision_does_not_cross_tenants() -> None:
    repository = MemoryDataProductRepository()
    for tenant in ("tenant-a", "tenant-b"):
        repository.create_operation_state(
            DataProductOperationState(
                "same-operation", tenant, "prod", "product", "manual_membership", "pending", 0, utc_now()
            )
        )
    assert repository.get_operation_state("tenant-a", "prod", "same-operation").tenant_id == "tenant-a"
    assert repository.get_operation_state("tenant-b", "prod", "same-operation").tenant_id == "tenant-b"


def test_cross_tenant_reconciliation_cannot_discover_operation() -> None:
    repository = MemoryDataProductRepository()
    repository.create_operation_state(
        DataProductOperationState(
            "private-operation", "tenant-a", "prod", "product", "manual_membership", "pending", 0, utc_now()
        )
    )
    service = DataProductOperationService(repository, worker_id="attacker")
    assert service.reconcile_operation("tenant-b", "prod", "private-operation") == "missing"


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="real Elasticsearch opt-in")
def test_real_persistence_cross_tenant_state_access_is_denied() -> None:
    repository = ElasticsearchDataProductRepository(Elasticsearch(os.environ["ELASTICSEARCH_URL"]))
    operation_id = f"security-{utc_now().timestamp()}"
    repository.create_operation_state(
        DataProductOperationState(
            operation_id, "tenant-a", "certification", "product", "manual_membership", "pending", 0, utc_now()
        )
    )
    assert repository.get_operation_state("tenant-b", "certification", operation_id) is None
    assert repository.get_operation_state("tenant-a", "other-environment", operation_id) is None
    assert repository.get_operation_state("tenant-a", "certification", operation_id) is not None
