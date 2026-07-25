from services.data_products.dependency_service import DataProductDependencyService
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.service import DataProductService
from tests.data_products.test_service import product


def test_empty_replace_is_serialized_replayable_and_tombstones():
    repository = MemoryDataProductRepository()
    products = DataProductService(repository)
    dependency = DataProductDependencyService(repository)
    upstream = products.create(product("upstream"), actor="seed")
    target = products.create(product("target"), actor="seed")
    first = dependency.replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [upstream.id],
        expected_etag=target.etag,
        actor="alice",
        reason="declare",
        idempotency_key="one",
    )
    replay = dependency.replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [upstream.id],
        expected_etag=target.etag,
        actor="alice",
        reason="declare",
        idempotency_key="one",
    )
    assert replay.replayed and replay.operation_id == first.operation_id
    removed = dependency.replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [],
        expected_etag=first.product.etag,
        actor="alice",
        reason="remove all",
        idempotency_key="two",
    )
    assert removed.dependencies == () and removed.removed_count == 1
    snapshot = repository.read_complete_dependency_snapshot("tenant-a", "default", "target", maximum=10)
    assert snapshot.complete and snapshot.dependencies[0].removed
    assert repository.get_product("tenant-a", "default", "target").revision == 3


def test_whitespace_is_rejected_but_empty_set_is_canonical():
    import pytest

    from services.data_products.dependency_events import canonical_upstream_ids

    assert canonical_upstream_ids("p", []) == ()
    with pytest.raises(ValueError, match="whitespace"):
        canonical_upstream_ids("p", ["  "])


def test_completed_replay_returns_immutable_result_after_later_mutation():
    repository = MemoryDataProductRepository()
    products = DataProductService(repository)
    dependency = DataProductDependencyService(repository)
    upstream = products.create(product("upstream"), actor="seed")
    target = products.create(product("target"), actor="seed")
    original = dependency.replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [upstream.id],
        expected_etag=target.etag,
        actor="alice",
        reason="declare",
        idempotency_key="original",
    )
    dependency.replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [],
        expected_etag=original.product.etag,
        actor="alice",
        reason="remove",
        idempotency_key="later",
    )
    replay = dependency.replace_declared_dependencies(
        "tenant-a",
        "default",
        "target",
        [upstream.id],
        expected_etag=target.etag,
        actor="alice",
        reason="declare",
        idempotency_key="original",
    )
    assert replay.replayed
    assert replay.product.revision == original.product.revision
    assert [edge.upstream_product_id for edge in replay.dependencies] == ["upstream"]
