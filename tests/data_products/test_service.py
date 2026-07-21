from datetime import datetime, timezone

import pytest

from packages.domain_model.data_product import (
    DataProduct,
    DataProductCriticality,
    DataProductDependency,
    DataProductOwner,
)
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.repository import ProductVersionConflict
from services.data_products.service import DataProductService


def product(identifier: str, dependencies: list[str] | None = None) -> DataProduct:
    return DataProduct(
        id=identifier,
        tenant_id="tenant-a",
        criticality=DataProductCriticality.HIGH,
        domain="sales",
        name=identifier,
        owner=DataProductOwner(team="data"),
        dependencies=[DataProductDependency(upstream_product_id=item) for item in dependencies or []],
        etag="",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_revision_increments_and_etag_covers_revision():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    created = service.create(product("orders"), actor="alice", reason="initial ownership")
    updated = service.update(
        created.model_copy(update={"name": "Orders"}),
        if_match=created.etag,
        actor="bob",
        reason="normalize name",
    )
    assert (created.revision, updated.revision) == (1, 2)
    assert created.etag != updated.etag
    assert len(repository.revisions) == 2


def test_recursive_dependency_cycle_is_rejected():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    a = service.create(product("a"), actor="alice")
    b = service.create(product("b", ["a"]), actor="alice")
    c = service.create(product("c", ["b"]), actor="alice")
    with pytest.raises(ValueError, match="cycle"):
        service.update(
            a.model_copy(update={"dependencies": [DataProductDependency(upstream_product_id="c")]}),
            if_match=a.etag,
            actor="alice",
        )
    assert b.revision == c.revision == 1


def test_divergent_revision_event_is_rejected():
    repository = MemoryDataProductRepository()
    value = product("orders")
    repository.append_revision(value, actor="alice", reason="created")
    with pytest.raises(ProductVersionConflict, match="divergent"):
        repository.append_revision(value.model_copy(update={"name": "different"}), actor="alice", reason="created")
