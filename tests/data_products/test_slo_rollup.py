from datetime import datetime, timedelta, timezone

from packages.domain_model.slo import DataReliabilitySLODefinition, IntervalEvidence, evaluate_intervals
from services.data_products.slo_evaluator import roll_up_child_slos


def child(identifier, classifications):
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    definition = DataReliabilitySLODefinition(
        id=identifier,
        tenant_id="t",
        scope_type="asset",
        scope_id=identifier,
        name=identifier,
        sli_type="quality",
        objective=0.9,
        window="24h",
        evaluation_granularity="1h",
        source_monitor_ids=[identifier],
        owner_team="team",
        etag="e",
        created_by="actor",
    )
    return evaluate_intervals(
        definition,
        [
            IntervalEvidence(classification=value, evidence_ref=f"{identifier}:{index}")
            for index, value in enumerate(classifications)
        ],
        window_start=now - timedelta(days=1),
        window_end=now,
        evaluated_at=now,
    )


def test_rollup_deduplicates_and_preserves_critical_cap():
    healthy = child("orders", ["good"] * 10)
    failed = child("payments", ["bad"] * 10)
    result = roll_up_child_slos([(healthy, 9, False), (failed, 1, True), (failed, 1, True)])
    assert result["actual_value"] == 0.9
    assert result["state"] == "failed"
    assert result["critical_component_cap_applied"] is True
    assert len(result["component_evaluation_ids"]) == 2
