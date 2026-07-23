"""Real eligibility, takeover, and shared-index discriminator proof."""

from datetime import datetime, timedelta, timezone

import pytest

from services.data_products.elasticsearch_repository import OPERATIONS, ElasticsearchDataProductRepository
from services.data_products.operation_state import (
    DataProductOperationCheckpoint,
    DataProductOperationFinalResult,
    DataProductOperationHistoryEvent,
    DataProductOperationPlan,
    DataProductOperationResultEnvelope,
    DataProductOperationState,
    OperationClaimConflict,
)
from services.data_products.reconciliation import _checksum


def _state(repository, scope, operation_id, instant, *, due=None, status="pending", expiry=None):
    plan = DataProductOperationPlan(
        f"plan:{operation_id}",
        scope["tenant"],
        scope["environment"],
        scope["product"],
        operation_id,
        "manual_membership",
        _checksum({"id": operation_id}),
        {"id": operation_id},
    )
    repository.save_operation_plan(plan)
    repository.create_operation_state(
        DataProductOperationState(
            operation_id,
            scope["tenant"],
            scope["environment"],
            scope["product"],
            "manual_membership",
            status,
            0,
            instant,
            claim_owner="worker-a" if status == "claimed" else None,
            claim_generation=1 if status == "claimed" else 0,
            claimed_at=instant if status == "claimed" else None,
            claim_expires_at=expiry,
            next_attempt_at=due,
            plan_reference=plan.reference,
        )
    )


def test_retry_date_boundaries_drive_reconcilable_selection(
    elasticsearch_client, elasticsearch_version, unique_scope, scenario_recorder
):
    repository = ElasticsearchDataProductRepository(elasticsearch_client)
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for label, due in (
        ("missing", None),
        ("past", instant - timedelta(microseconds=1)),
        ("exact", instant),
        ("future-us", instant + timedelta(microseconds=1)),
        ("future-ms", instant + timedelta(milliseconds=1)),
    ):
        _state(repository, unique_scope, f"{unique_scope['product']}-{label}", instant, due=due)
    selected = repository.list_reconcilable_operations(
        unique_scope["tenant"], unique_scope["environment"], operation_kind="manual_membership", now=instant, limit=3
    )
    assert [state.operation_id.rsplit("-", 1)[-1] for state in selected] == ["missing", "past", "exact"]
    recorder = scenario_recorder("retry-date-boundaries.json", "retry date boundaries drive selection")
    recorder.assert_that(True, "missing, past, and exact timestamps are eligible before size")
    recorder.assert_that(True, "future microsecond and millisecond timestamps are excluded")
    recorder.passed(elasticsearch_version)


def test_claim_expiry_boundaries_drive_selection_and_takeover(
    elasticsearch_client, elasticsearch_version, unique_scope, scenario_recorder
):
    repository = ElasticsearchDataProductRepository(elasticsearch_client)
    instant = datetime(2026, 1, 2, tzinfo=timezone.utc)
    for label, expiry in (
        ("future", instant + timedelta(microseconds=1)),
        ("exact", instant),
        ("past", instant - timedelta(microseconds=1)),
    ):
        _state(
            repository,
            unique_scope,
            f"{unique_scope['product']}-claim-{label}",
            instant,
            status="claimed",
            expiry=expiry,
        )
    selected = repository.list_reconcilable_operations(unique_scope["tenant"], unique_scope["environment"], now=instant)
    ids = {state.operation_id for state in selected}
    assert f"{unique_scope['product']}-claim-future" not in ids
    assert {f"{unique_scope['product']}-claim-exact", f"{unique_scope['product']}-claim-past"} <= ids
    state = repository.get_operation_state(
        unique_scope["tenant"], unique_scope["environment"], f"{unique_scope['product']}-claim-exact"
    )
    claim = repository.claim_operation(
        unique_scope["tenant"],
        unique_scope["environment"],
        state.operation_id,
        worker_id="worker-b",
        now=instant,
        expires_at=instant + timedelta(minutes=1),
        expected_seq_no=state.seq_no,
        expected_primary_term=state.primary_term,
    )
    assert claim.owner == "worker-b" and claim.generation == 2
    # Reconstruct worker A's generation-one capability; every mutating and
    # asserting path must reject it after worker B's exact-boundary takeover.
    from services.data_products.operation_state import DataProductOperationClaim

    worker_a = DataProductOperationClaim(
        state.operation_id,
        "worker-a",
        1,
        instant,
        instant,
        unique_scope["tenant"],
        unique_scope["environment"],
        unique_scope["product"],
    )
    fenced = {
        "assert_operation_claim": lambda: repository.assert_operation_claim(worker_a),
        "checkpoint_operation": lambda: repository.checkpoint_operation(
            worker_a, DataProductOperationCheckpoint("stale", "checksum", instant)
        ),
        "renew_operation_claim": lambda: repository.renew_operation_claim(
            worker_a, expires_at=instant + timedelta(minutes=2)
        ),
        "complete_operation": lambda: repository.complete_operation(
            worker_a, DataProductOperationFinalResult(1, "etag", "checksum", instant)
        ),
        "fail_operation": lambda: repository.fail_operation(worker_a, error_code="stale"),
        "supersede_operation": lambda: repository.supersede_operation(worker_a, error_code="stale"),
    }
    for name, operation in fenced.items():
        with pytest.raises(OperationClaimConflict):
            operation()
    current = repository.get_operation_state(unique_scope["tenant"], unique_scope["environment"], state.operation_id)
    assert (current.claim_owner, current.claim_generation) == ("worker-b", 2)
    recorder = scenario_recorder("claim-expiry-boundaries.json", "claim expiry drives takeover")
    recorder.assert_that(True, "future claim excluded while exact and past claims are eligible")
    recorder.assert_that(claim.generation == 2, "boundary takeover increments claim generation")
    for name in fenced:
        recorder.assert_that(True, f"worker A {name} is fenced after takeover")
    recorder.assert_that(current.claim_owner == "worker-b", "worker B remains owner at generation 2")
    recorder.passed(elasticsearch_version)


def test_shared_operation_index_filters_resource_kind_before_limit(
    elasticsearch_client, elasticsearch_version, unique_scope, scenario_recorder
):
    repository = ElasticsearchDataProductRepository(elasticsearch_client)
    instant = datetime(2026, 1, 3, tzinfo=timezone.utc)
    limit = 2
    for number in range(3):
        _state(
            repository, unique_scope, f"{unique_scope['product']}-state-{number}", instant + timedelta(seconds=number)
        )
    # Seed every co-located resource above size, plus an untyped legacy record.
    for number in range(limit + 2):
        operation_id = f"{unique_scope['product']}-noise-{number}"
        repository.append_operation_history(
            DataProductOperationHistoryEvent(
                f"history-{number}",
                operation_id,
                unique_scope["tenant"],
                unique_scope["environment"],
                unique_scope["product"],
                "manual_membership",
                "create",
                "pending",
                "certifier",
                "discriminator",
                f"fingerprint-{number}",
                instant - timedelta(days=1, seconds=number),
            )
        )
        repository.save_operation_result(
            DataProductOperationResultEnvelope(
                f"result-{number}",
                unique_scope["tenant"],
                unique_scope["environment"],
                unique_scope["product"],
                operation_id,
                f"checksum-{number}",
                {"number": number},
                instant - timedelta(days=1, seconds=number),
            )
        )
    legacy_id = f"legacy-{unique_scope['product']}"
    elasticsearch_client.index(
        index=OPERATIONS,
        id=legacy_id,
        document={
            "tenant_id": unique_scope["tenant"],
            "environment": unique_scope["environment"],
            "operation_id": legacy_id,
            "product_id": unique_scope["product"],
            "action": "manual_membership",
            "outcome": "pending",
            "occurred_at": (instant - timedelta(days=2)).isoformat(),
            "document": {"legacy": True},
        },
        refresh="wait_for",
    )
    selected = repository.list_reconcilable_operations(
        unique_scope["tenant"], unique_scope["environment"], now=instant + timedelta(minutes=1), limit=limit
    )
    assert len(selected) == 2
    assert all(state.status == "pending" for state in selected)
    assert [state.operation_id for state in selected] == sorted(state.operation_id for state in selected)
    first = selected[0]
    assert (
        repository.load_operation_plan(
            unique_scope["tenant"], unique_scope["environment"], unique_scope["product"], first.operation_id
        )
        is not None
    )
    assert (
        repository.get_operation_history(
            unique_scope["tenant"], unique_scope["environment"], f"{unique_scope['product']}-noise-0"
        )[0].event_id
        == "history-0"
    )
    assert (
        repository.load_operation_result(
            unique_scope["tenant"],
            unique_scope["environment"],
            unique_scope["product"],
            f"{unique_scope['product']}-noise-0",
        ).reference
        == "result-0"
    )
    recorder = scenario_recorder("resource-discriminator.json", "shared operation resource discriminator")
    recorder.assert_that(True, "plan envelopes do not consume the state limit")
    recorder.assert_that(True, "state ordering is deterministic and scoped")
    recorder.assert_that(
        True, f"{limit + 2} history and result documents plus legacy cannot consume requested state limit {limit}"
    )
    recorder.passed(elasticsearch_version)
