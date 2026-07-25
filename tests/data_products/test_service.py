from datetime import datetime, timezone

import pytest

from packages.domain_model.data_product import (
    DataProduct,
    DataProductCriticality,
    DataProductDependency,
    DataProductOutput,
    DataProductOwner,
)
from services.data_products.idempotency import IdempotencyConflict
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


def test_lifecycle_idempotency_key_reaches_pending_operation_identity():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    draft = product("orders")
    draft.outputs = [DataProductOutput(entity_id="orders-table", entity_type="asset")]
    created = service.create(draft, actor="alice", idempotency_key="create-request")

    activated = service.activate(
        created.tenant_id,
        created.environment,
        created.id,
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="activate-request",
    )

    applied = [event for event, _ in repository.operations.values() if event.action == "activate"]
    assert activated.lifecycle_state == "active"
    assert len(applied) == 1
    expected = service._pending(activated, "alice", "ready", "activate", "activate-request")
    assert applied[0].operation_id == expected.operation_id


def test_completed_lifecycle_replays_before_state_and_etag_validation():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    draft = product("orders")
    draft.outputs = [DataProductOutput(entity_id="orders-table", entity_type="asset")]
    created = service.create(draft, actor="alice", idempotency_key="create-request")
    activated = service.activate(
        created.tenant_id,
        created.environment,
        created.id,
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="activate-request",
    )

    replay = service.activate(
        created.tenant_id,
        created.environment,
        created.id,
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="activate-request",
    )

    assert replay.model_dump() == activated.model_dump()
    assert len([event for event, _ in repository.operations.values() if event.action == "activate"]) == 1


def test_completed_lifecycle_replays_immutable_result_after_later_revision():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    draft = product("orders")
    draft.outputs = [DataProductOutput(entity_id="orders-table", entity_type="asset")]
    created = service.create(draft, actor="alice", idempotency_key="create-request")
    activated = service.activate(
        created.tenant_id,
        created.environment,
        created.id,
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="activate-request",
    )
    deprecated = service.deprecate(
        activated.tenant_id,
        activated.environment,
        activated.id,
        if_match=activated.etag,
        actor="alice",
        reason="replacement available",
        idempotency_key="deprecate-request",
    )

    replay = service.activate(
        created.tenant_id,
        created.environment,
        created.id,
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="activate-request",
    )

    assert deprecated.revision == 3
    assert (replay.revision, replay.etag, replay.lifecycle_state) == (
        activated.revision,
        activated.etag,
        "active",
    )
    record = next(item for item in repository.idempotency.values() if item.action == "activate")
    assert record.action == "activate"


def test_lifecycle_key_cannot_be_reused_for_divergent_request():
    repository = MemoryDataProductRepository()
    service = DataProductService(repository)
    draft = product("orders")
    draft.outputs = [DataProductOutput(entity_id="orders-table", entity_type="asset")]
    created = service.create(draft, actor="alice", idempotency_key="create-request")
    service.activate(
        created.tenant_id,
        created.environment,
        created.id,
        if_match=created.etag,
        actor="alice",
        reason="ready",
        idempotency_key="same-key",
    )
    with pytest.raises(IdempotencyConflict, match="idempotency_conflict"):
        service.deprecate(
            created.tenant_id,
            created.environment,
            created.id,
            if_match=created.etag,
            actor="alice",
            reason="ready",
            idempotency_key="same-key",
        )
