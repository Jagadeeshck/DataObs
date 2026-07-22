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
from services.data_products.reconciliation import (
    DataProductOperationService,
    ManualMembershipReconciliationHandler,
    OperationReconciliationRegistry,
    _checksum,
)


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


def test_plan_result_payload_is_not_false_projection_evidence() -> None:
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
            _checksum(
                {
                    "request_fingerprint": "fingerprint",
                    "membership_id": "missing",
                    "entity_id": "e",
                    "entity_type": "table",
                    "result": {"revision": 4, "etag": "etag-4"},
                }
            ),
            {
                "request_fingerprint": "fingerprint",
                "membership_id": "missing",
                "entity_id": "e",
                "entity_type": "table",
                "result": {"revision": 4, "etag": "etag-4"},
            },
        )
    )

    assert (
        DataProductOperationService(repository, worker_id="worker").reconcile_operation("tenant", "prod", "recover-me")
        == "failed"
    )
    completed = repository.get_operation_state("tenant", "prod", "recover-me")
    assert completed.status == "failed"
    assert repository.load_operation_result("tenant", "prod", "product", "recover-me") is None


def test_typed_missing_result_does_not_disclose_worker() -> None:
    result = DataProductOperationService(MemoryDataProductRepository(), worker_id="secret-worker").reconcile_operation(
        "tenant", "prod", "missing"
    )
    assert result.status == "missing"
    assert result.operation_kind is None
    assert "secret-worker" not in repr(result)


def test_attempt_limit_uses_claimed_attempt_without_off_by_one() -> None:
    repository = MemoryDataProductRepository()
    initial = state("exhausted")
    initial = initial.__class__(**{**initial.__dict__, "attempt_count": 0})
    repository.add_operation_state(initial)
    result = DataProductOperationService(repository, worker_id="worker", max_attempts=1).reconcile_operation(
        "tenant", "prod", "exhausted"
    )
    assert result.status == "failed"
    assert result.attempt_count == 1
    assert result.error_code == "reconciliation_attempts_exhausted"


def test_registry_has_distinct_concrete_handlers() -> None:
    registry = OperationReconciliationRegistry()
    handlers = [registry.get(kind) for kind in registry.REQUIRED_KINDS]
    assert isinstance(registry.get("manual_membership"), ManualMembershipReconciliationHandler)
    assert len({type(handler) for handler in handlers}) == len(handlers)


@pytest.mark.parametrize("terminal", ["applied", "failed", "superseded"])
def test_terminal_replay_preserves_underlying_status(terminal: str) -> None:
    repository = MemoryDataProductRepository()
    initial = state(f"terminal-{terminal}")
    repository.add_operation_state(initial.__class__(**{**initial.__dict__, "status": terminal}))

    result = DataProductOperationService(repository, worker_id="worker").reconcile_operation(
        "tenant", "prod", f"terminal-{terminal}"
    )

    assert result.status == terminal
    assert result.replayed is True
    assert result.recovered is False
    assert result.retryable is False


def test_operation_kind_filter_is_applied_before_limit() -> None:
    repository = MemoryDataProductRepository()
    for index in range(3):
        repository.add_operation_state(state(f"dependency-{index}"))
    wanted = state("manual")
    repository.add_operation_state(wanted.__class__(**{**wanted.__dict__, "operation_kind": "manual_membership"}))

    selected = repository.list_reconcilable_operations("tenant", "prod", limit=1, operation_kind="manual_membership")

    assert [item.operation_id for item in selected] == ["manual"]
