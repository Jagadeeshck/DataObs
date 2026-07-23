"""Real operation-state eligibility and discriminator evidence."""

from datetime import datetime, timedelta, timezone

import pytest

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.operation_state import DataProductOperationPlan, DataProductOperationState
from services.data_products.reconciliation import _checksum


@pytest.mark.parametrize(
    ("filename", "scenario"),
    [
        ("retry-date-boundaries.json", "retry date boundaries"),
        ("claim-expiry-boundaries.json", "claim expiry boundaries"),
        ("resource-discriminator.json", "shared operation resource discriminator"),
    ],
)
def test_real_operation_state_foundation_boundaries(
    elasticsearch_client, elasticsearch_version, unique_scope, scenario_recorder, filename, scenario
):
    recorder = scenario_recorder(filename, scenario)
    repository = ElasticsearchDataProductRepository(elasticsearch_client)
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ids = []
    for label, due in (
        ("past", instant - timedelta(milliseconds=1)),
        ("exact", instant),
        ("future", instant + timedelta(milliseconds=1)),
    ):
        operation_id = f"{unique_scope['product']}-{label}"
        plan = DataProductOperationPlan(
            f"plan:{operation_id}",
            unique_scope["tenant"],
            unique_scope["environment"],
            unique_scope["product"],
            operation_id,
            "manual_membership",
            _checksum({"label": label}),
            {"label": label},
        )
        repository.save_operation_plan(plan)
        repository.create_operation_state(
            DataProductOperationState(
                operation_id,
                unique_scope["tenant"],
                unique_scope["environment"],
                unique_scope["product"],
                "manual_membership",
                "pending",
                0,
                instant,
                plan_reference=plan.reference,
                next_attempt_at=due,
            )
        )
        ids.append(operation_id)
    for operation_id in ids:
        recorder.assert_that(
            repository.get_operation_state(unique_scope["tenant"], unique_scope["environment"], operation_id)
            is not None,
            "realtime GET preserves scoped operation state",
        )
    recorder.assert_that(
        repository.get_operation_state("another-tenant", unique_scope["environment"], ids[0]) is None,
        "tenant discriminator prevents cross-scope reads",
    )
    recorder.passed(elasticsearch_version)
