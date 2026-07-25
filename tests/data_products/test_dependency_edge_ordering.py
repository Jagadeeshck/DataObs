from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductDependencyProjection
from services.data_products.events import ProductConsistencyError
from services.data_products.memory_repository import MemoryDataProductRepository


def edge(revision: int, *, removed: bool = False):
    now = utc_now()
    return DataProductDependencyProjection(
        tenant_id="tenant",
        environment="prod",
        product_id="product",
        upstream_product_id="upstream",
        product_revision=revision,
        graph_version=f"graph-{revision}",
        removed=removed,
        removed_at=now if removed else None,
        removed_by_revision=revision if removed else None,
    )


def test_stale_dependency_worker_cannot_overwrite_newer_edge():
    repository = MemoryDataProductRepository()
    repository.apply_dependency_upsert_chunk("tenant", "prod", "product", (edge(2),))

    try:
        repository.apply_dependency_upsert_chunk("tenant", "prod", "product", (edge(1),))
    except ProductConsistencyError as exc:
        assert str(exc) == "dependency_edge_superseded"
    else:
        raise AssertionError("stale edge write was accepted")

    assert repository.dependencies[("tenant", "prod", "product", "upstream")].product_revision == 2


def test_dependency_chunk_contract_discriminates_tombstones():
    repository = MemoryDataProductRepository()
    try:
        repository.apply_dependency_tombstone_chunk("tenant", "prod", "product", (edge(1),))
    except ProductConsistencyError as exc:
        assert str(exc) == "dependency_edge_removed_semantics_invalid"
    else:
        raise AssertionError("active edge was accepted by tombstone API")
