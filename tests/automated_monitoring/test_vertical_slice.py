from datetime import datetime, timezone

from packages.domain_model.data_product import DataProductReliability
from packages.domain_model.monitor import ColdStartState, MonitorBaselinePolicy, MonitorThresholdPolicy, ThresholdMode
from services.monitor_recommender.coverage import calculate_coverage
from services.monitoring.baseline_engine import build_baseline
from services.monitoring.evaluator import is_breach
from services.monitoring.robust_statistics import categorical_divergence, median_absolute_deviation
from services.product_query.data_product_reliability import score_reliability
from services.rca.hypothesis_engine import EvidenceRef, Hypothesis, score_hypotheses
from services.rca.hypothesis_rules import HypothesisType


def test_robust_baseline_resists_outlier_and_explains_calculation():
    policy = MonitorBaselinePolicy(minimum_samples=6, method="mad", sensitivity="medium", seasonality=["hour_of_day"])
    result = build_baseline([99, 100, 100, 101, 100, 1000], policy, datetime(2026, 7, 19, 8, tzinfo=timezone.utc))
    assert result.cold_start_state == ColdStartState.MATURE
    assert result.expected_range is not None and result.expected_range.maximum < 200
    assert "MAD" in result.expected_range.calculation
    assert result.seasonal_cohort == "hour=8"
    assert median_absolute_deviation([1, 1, 2, 2, 100]) == 1


def test_immature_learned_threshold_does_not_claim_breach_without_safety_bound():
    learned = build_baseline(
        [10, 11, 12], MonitorBaselinePolicy(minimum_samples=10), datetime.now(timezone.utc)
    ).expected_range
    learned_only = MonitorThresholdPolicy(mode=ThresholdMode.LEARNED)
    hybrid = MonitorThresholdPolicy(mode=ThresholdMode.HYBRID, fixed_safety_maximum=50)
    assert not is_breach(100, learned_only, learned, ColdStartState.COLLECTING)
    assert is_breach(100, hybrid, learned, ColdStartState.COLLECTING)


def test_distribution_divergence_is_bounded():
    assert categorical_divergence({"a": 100}, {"b": 100}) == 1
    assert categorical_divergence({"a": 50, "b": 50}, {"a": 50, "b": 50}) == 0


def test_coverage_is_category_aware():
    coverage = calculate_coverage("asset", "orders", {"freshness", "volume", "schema"}, {"freshness"}, {"volume"})
    assert coverage.state == "partially_covered"
    assert coverage.numerator == 1 and coverage.denominator == 3
    assert coverage.high_risk_gaps == ["schema", "volume"]


def test_missing_reliability_evidence_reduces_confidence_not_health():
    score = score_reliability({"freshness": 100, "quality": None}, {"freshness": 0.5, "quality": 0.5}, "7d")
    assert isinstance(score, DataProductReliability)
    assert score.overall_score == 100
    assert score.confidence == 0.5
    assert score.missing_components == ["quality"]


def test_rca_ranking_is_deterministic_and_preserves_contradictions():
    evidence = EvidenceRef(source_document_ref="deployment:abc", summary="deployment preceded breach", strength=0.9)
    contradiction = EvidenceRef(source_document_ref="asset:upstream", summary="upstream remained healthy", strength=0.8)
    hypothesis = Hypothesis(
        type=HypothesisType.DEPLOYMENT_CHANGE,
        title="Recent deployment",
        description="Deployment was temporally close",
        suspected_entity="service:writer",
        time_relationship="2m before",
        supporting_evidence=[evidence],
        contradicting_evidence=[contradiction],
        missing_evidence=["rollback verification"],
        confidence=0,
        impact="orders stale",
        deterministic_rule_ids=["RCA-DEPLOY-001"],
        recommended_next_check="compare deployment version",
        safe_action_candidates=["request owner review"],
    )
    ranked = score_hypotheses(
        [
            (
                hypothesis,
                {"temporal_proximity": 1, "evidence_strength": 0.9, "incident_compatibility": 1, "contradictions": 0.8},
            )
        ]
    )
    assert ranked[0].rank == 1
    assert ranked[0].classification == "insufficient_evidence"
    assert ranked[0].score_breakdown["contradictions"] < 0
