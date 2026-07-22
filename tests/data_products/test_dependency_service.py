"""Dependency runtime completion contracts."""

from services.data_products.dependency_service import DataProductDependencyService
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.service import DataProductService
from tests.data_products.test_service import product


def test_normal_dependency_success_finishes_generic_state() -> None:
    repository = MemoryDataProductRepository()
    products = DataProductService(repository)
    upstream = products.create(product("upstream"), actor="seed")
    target = products.create(product("target"), actor="seed")
    result = DataProductDependencyService(repository).replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [upstream.id],
        expected_etag=target.etag,
        actor="alice",
        reason="declare",
        idempotency_key="dependencies-1",
    )
    state = repository.get_operation_state("tenant-a", "default", result.operation_id)
    assert state is not None and state.status == "applied" and state.result_reference
    assert len(result.dependencies) == 1
