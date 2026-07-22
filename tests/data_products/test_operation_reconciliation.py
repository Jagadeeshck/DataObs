from datetime import timedelta

import pytest

from packages.domain_model.base import utc_now
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.operation_state import (
    DataProductOperationFinalResult,
    DataProductOperationPlan,
    DataProductOperationState,
    OperationClaimConflict,
)
from services.data_products.reconciliation import DataProductOperationService, OperationReconciliationRegistry


def state(operation_id: str = "op-1") -> DataProductOperationState:
    return DataProductOperationState(
        operation_id, "tenant", "prod", "product", "dependency_replace", "pending", 0, utc_now()
    )


def test_claim_generation_and_stale_worker_fencing() -> None:
    repository = MemoryDataProductRepository()
    initial = state()
    repository.add_operation_state(initial)
    now = utc_now()
    first = repository.claim_operation(
        "tenant",
        "prod",
        "op-1",
        worker_id="one",
        now=now,
        expires_at=now + timedelta(seconds=1),
        expected_seq_no=0,
        expected_primary_term=1,
    )
    claimed = repository.get_operation_state("tenant", "prod", "op-1")
    second = repository.claim_operation(
        "tenant",
        "prod",
        "op-1",
        worker_id="two",
        now=now + timedelta(seconds=2),
        expires_at=now + timedelta(seconds=30),
        expected_seq_no=claimed.seq_no,
        expected_primary_term=claimed.primary_term,
    )
    assert second.generation == first.generation + 1
    with pytest.raises(OperationClaimConflict, match="stale_operation_claim"):
        repository.complete_operation(first, DataProductOperationFinalResult(1, "etag", "checksum", now))


def test_history_is_create_or_canonical_verify() -> None:
    from services.data_products.operation_state import DataProductOperationHistoryEvent

    repository = MemoryDataProductRepository()
    event = DataProductOperationHistoryEvent(
        "event",
        "op",
        "tenant",
        "prod",
        "product",
        "manual_membership",
        "create",
        "pending",
        "actor",
        "reason",
        "fingerprint",
        utc_now(),
    )
    repository.append_operation_history(event)
    repository.append_operation_history(event)
    with pytest.raises(RuntimeError, match="divergent immutable"):
        repository.append_operation_history(event.__class__(**{**event.__dict__, "reason": "poisoned"}))


def test_registry_rejects_unknown_operation_kind() -> None:
    from services.data_products.operation_state import OperationConsistencyError

    with pytest.raises(OperationConsistencyError, match="unknown_operation_kind"):
        OperationReconciliationRegistry().get("poisoned")


def test_durable_plan_is_recovered_before_state_completion() -> None:
    repository = MemoryDataProductRepository()
    initial = state("recover-me")
    initial = initial.__class__(
        **{**initial.__dict__, "operation_kind": "manual_membership", "plan_reference": "plan-1"}
    )
    repository.add_operation_state(initial)
    repository.save_operation_plan(
        DataProductOperationPlan(
            "plan-1",
            "tenant",
            "prod",
            "product",
            "recover-me",
            "manual_membership",
            "plan-checksum",
            {"result": {"revision": 4, "etag": "etag-4"}},
        )
    )

    assert (
        DataProductOperationService(repository, worker_id="worker").reconcile_operation("tenant", "prod", "recover-me")
        == "applied"
    )
    completed = repository.get_operation_state("tenant", "prod", "recover-me")
    assert completed.status == "applied"
    assert repository.load_operation_result("tenant", "prod", "product", "recover-me") is not None
