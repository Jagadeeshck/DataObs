from datetime import datetime, timedelta, timezone

from packages.domain_model.incident import Incident
from services.incident_manager.correlation.policy import V1_POLICY
from services.incident_manager.correlation.service import CorrelationService
from services.incident_manager.flood_control.contracts import FloodEvent, FloodState, FloodWindow
from services.incident_manager.flood_control.evaluator import evaluate_flood
from services.incident_manager.flood_control.policy import FloodPolicy

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def incident(identifier: str, tenant="t1", environment="prod", assets=None):
    return Incident(
        id=identifier,
        tenant_id=tenant,
        environment=environment,
        deduplication_key=identifier,
        affected_assets=assets or [],
        first_observed_at=NOW,
        last_observed_at=NOW,
    )


def test_policy_hash_and_decision_are_stable_and_explainable():
    first = incident("one", assets=["asset-1"])
    second = incident("two", assets=["asset-1"])
    result = CorrelationService().evaluate(first, second, revision="7")
    replay = CorrelationService().evaluate(first, second, revision="7")
    assert result.action == "attach"
    assert result.decision_id == replay.decision_id
    assert result.policy_hash == V1_POLICY.canonical_hash
    assert "same_asset" in result.reason_codes
    assert "not a causal conclusion" in result.wording


def test_missing_evidence_does_not_inflate_confidence_and_scope_is_absolute():
    empty = CorrelationService().evaluate(incident("one"), incident("two"), revision="1")
    crossed = CorrelationService().evaluate(incident("one"), incident("two", tenant="t2"), revision="1")
    assert empty.action == "insufficient_evidence"
    assert empty.confidence == 0
    assert crossed.action == "reject"
    assert crossed.reason_codes == ("scope_incompatible",)


def test_event_time_threshold_replay_and_critical_bypass():
    policy = FloodPolicy(elevated_count=2, flooding_count=3, event_rate_per_minute=100, unique_asset_threshold=99)
    window = FloodWindow("f1", "t1", "prod", "g1")
    decision, window = evaluate_flood(window, FloodEvent("e1", NOW, "i1"), policy)
    assert decision.new_state == FloodState.NORMAL
    elevated, window = evaluate_flood(window, FloodEvent("e2", NOW + timedelta(seconds=1), "i2"), policy)
    assert elevated.new_state == FloodState.ELEVATED
    flooding, window = evaluate_flood(window, FloodEvent("e3", NOW + timedelta(seconds=2), "i3"), policy)
    assert flooding.new_state == FloodState.FLOODING
    assert flooding.notification_decision == "coalesce"
    assert evaluate_flood(window, FloodEvent("e3", NOW + timedelta(seconds=2), "i3"), policy)[0].observed["count"] == 3
    bypass, window = evaluate_flood(
        window, FloodEvent("e4", NOW + timedelta(seconds=3), "i4", severity="critical"), policy
    )
    assert bypass.notification_decision == "escalate"


def test_storage_is_bounded_deterministically():
    policy = FloodPolicy(maximum_events=2, elevated_count=99, flooding_count=100)
    window = FloodWindow("f1", "t1", "prod", "g1")
    for n in range(3):
        _, window = evaluate_flood(window, FloodEvent(f"e{n}", NOW + timedelta(seconds=n), f"i{n}"), policy)
    assert sorted(window.events) == ["e1", "e2"]
