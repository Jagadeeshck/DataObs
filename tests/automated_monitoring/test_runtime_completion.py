from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.monitor import ColdStartState, MonitorThresholdPolicy, ThresholdMode
from services.monitor_recommender.service import InvalidRecommendationTransition, generate, transition
from services.monitoring.evaluator import evaluate
from services.monitoring.scheduler import interval_due
from services.rca.investigation_service import Evidence, investigate

NOW = datetime(2026, 7, 19, 12, tzinfo=timezone.utc)


def test_schedule_catch_up_is_bounded_and_idempotent():
    args = dict(
        tenant="a",
        environment="prod",
        monitor_id="m1",
        revision=2,
        target="asset:x",
        last_scheduled=NOW - timedelta(hours=10),
        now=NOW,
        interval=timedelta(hours=1),
        max_catch_up=3,
    )
    first = interval_due(**args)
    assert len(first) == 3
    assert first == interval_due(**args)
    assert len({item.evaluation_key for item in first}) == 3


def test_evaluation_explains_hybrid_breach_and_missing_learned_input():
    policy = MonitorThresholdPolicy(mode=ThresholdMode.HYBRID, fixed_safety_maximum=50)
    decision = evaluate(
        60,
        policy,
        None,
        ColdStartState.COLLECTING,
        method="mad",
        sensitivity="medium",
        baseline_version=None,
        sample_count=2,
        confidence=0.2,
    )
    assert decision.state == "breached"
    assert decision.fixed_threshold["safety_maximum"] == 50
    assert decision.missing_inputs == ("learned_threshold",)


def test_evaluation_can_be_suppressed_but_source_failure_cannot():
    policy = MonitorThresholdPolicy(mode=ThresholdMode.FIXED, maximum=10)
    assert (
        evaluate(
            11,
            policy,
            None,
            ColdStartState.MATURE,
            method="fixed",
            sensitivity="medium",
            baseline_version=None,
            sample_count=0,
            confidence=1,
            suppressed=True,
        ).state
        == "suppressed"
    )
    assert (
        evaluate(
            None,
            policy,
            None,
            ColdStartState.MATURE,
            method="fixed",
            sensitivity="medium",
            baseline_version=None,
            sample_count=0,
            confidence=0,
            suppressed=True,
            source_available=False,
        ).state
        == "source_unavailable"
    )


def test_recommendations_are_deterministic_deduplicated_and_approval_gated():
    metadata = {"timestamp_columns": ["updated_at"], "primary_key": ["id"], "criticality": "high"}
    recs = generate("tenant-a", "orders", metadata, {("orders", "volume")})
    assert "volume" not in {str(item.monitor_type) for item in recs}
    assert generate("tenant-a", "orders", metadata, {("orders", "volume")})[0].id == recs[0].id
    rejected = transition(recs[0], "rejected")
    with pytest.raises(InvalidRecommendationTransition):
        transition(rejected, "accepted")


def test_rca_filters_tenant_and_ranks_support_and_contradiction_deterministically():
    evidence = [
        Evidence(
            "deployment",
            "deploy:1",
            NOW,
            "tenant-a",
            "prod",
            "service:writer",
            0.9,
            attributes={"temporal_proximity": 1, "summary": "deployment preceded incident"},
        ),
        Evidence(
            "source_health",
            "source:1",
            NOW,
            "tenant-a",
            "prod",
            "source:db",
            0.8,
            attributes={"contradicts": True, "summary": "source remained healthy"},
        ),
        Evidence("failed_query", "query:fingerprint", NOW, "tenant-b", "prod", "job:x", 1),
    ]
    result = investigate("inc-1", "tenant-a", "prod", evidence)
    assert result.investigation_id.startswith("rca-")
    assert len(result.hypotheses) == 2
    assert all(h.suspected_entity != "job:x" for h in result.hypotheses)
    assert any(h.contradicting_evidence for h in result.hypotheses)
