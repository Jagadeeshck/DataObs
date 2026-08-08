from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.monitor import BaselineMode, BaselineState, MonitorBaselinePolicy
from services.monitoring.adaptive_engine import HistoricalPoint, evaluate_adaptive
from services.monitoring.distribution_drift import (
    NumericalProfile,
    compare_categorical,
    compare_numerical,
    jensen_shannon,
    population_stability_index,
    top_k_profile,
)

NOW = datetime(2026, 8, 8, 8, tzinfo=timezone.utc)


def points(values, *, start=None, **flags):
    start = start or NOW - timedelta(days=max(len(values) - 1, 1))
    return [HistoricalPoint(float(value), start + timedelta(days=index), **flags) for index, value in enumerate(values)]


@pytest.mark.parametrize("method", ["mad", "iqr", "quantile", "rolling_median"])
def test_deterministic_methods_detect_volume_drop(method):
    policy = MonitorBaselinePolicy(method=method, minimum_samples=14, history_points=60)
    result = evaluate_adaptive(410_000, points([1_000_000 + (i % 3) * 1000 for i in range(28)]), policy, NOW)
    assert result.state == BaselineState.READY
    assert result.breached
    assert result.anomaly_score == 100
    assert result.observed_value == 410_000


def test_cold_start_never_claims_detection_active():
    result = evaluate_adaptive(0, points([0, 0]), MonitorBaselinePolicy(), NOW)
    assert result.state == BaselineState.COLLECTING
    assert not result.breached
    assert result.anomaly_score is None
    assert "sufficient_history" in result.missing_inputs


def test_zero_is_an_observation_not_missing():
    result = evaluate_adaptive(0, points([100] * 20), MonitorBaselinePolicy(), NOW)
    assert result.observed_value == 0
    assert "observation" not in result.missing_inputs
    assert result.breached


def test_hybrid_safety_bound_constrains_adaptive_range():
    policy = MonitorBaselinePolicy(mode=BaselineMode.HYBRID, minimum_samples=5)
    result = evaluate_adaptive(
        600, points([100, 101, 99, 100, 100, 101, 99]), policy, NOW, safety_minimum=90, safety_maximum=500
    )
    assert result.expected_lower >= 90
    assert result.expected_upper <= 500


def test_seasonal_weekend_and_fallback_are_explainable():
    policy = MonitorBaselinePolicy(minimum_samples=3, seasonality=["weekday_weekend"])
    history = points([100, 100, 100, 100, 100, 100, 100])
    result = evaluate_adaptive(100, history, policy, NOW)
    assert result.cohort == "weekend"
    assert result.cohort_fallback_reason is not None
    assert result.confidence == 0.75


@pytest.mark.parametrize(
    "flag,reason",
    [
        ("breached", "prior_breach"),
        ("backfill", "backfill"),
        ("maintenance", "maintenance"),
        ("stale", "stale"),
        ("complete", "incomplete_evidence"),
    ],
)
def test_contamination_exclusions(flag, reason):
    kwargs = {flag: False if flag == "complete" else True}
    policy = MonitorBaselinePolicy(minimum_samples=3)
    history = points([100] * 10) + points([0], start=NOW - timedelta(hours=3), **kwargs)
    result = evaluate_adaptive(100, history, policy, NOW)
    assert reason in result.exclusions


def test_learning_delay_prevents_catastrophic_drop_from_learning():
    policy = MonitorBaselinePolicy(minimum_samples=5)
    history = points([100] * 10) + points([0], start=NOW - timedelta(hours=3))
    result = evaluate_adaptive(0, history, policy, NOW)
    assert result.breached
    assert result.center == 100
    assert "learning_delay" in result.exclusions


def profile(histogram=(10, 20, 10), median=45, null_count=2, outlier=0.01):
    return NumericalProfile(
        1000, null_count, {"p05": 10, "p25": 30, "p50": median, "p75": 60, "p95": 90}, histogram, outlier
    )


def test_numerical_distribution_shift_is_explainable():
    result = compare_numerical(profile(), profile((1, 4, 35), median=81, null_count=180, outlier=0.2))
    assert result.js_divergence > 0.2
    assert result.quantile_drift["p50"] > 1
    assert result.null_rate_change > 0.1
    assert result.outlier_ratio_change > 0.1


def test_divergence_edge_cases_are_finite():
    for calculation in (jensen_shannon, population_stability_index):
        value = calculation([0, 0, 0], [0, 10, 0])
        assert value >= 0
        assert value < float("inf")
    with pytest.raises(ValueError):
        jensen_shannon([1], [1, 2])


def test_categorical_top_k_other_and_dominant_changes():
    compact = top_k_profile({f"category-{i}": i for i in range(100)}, top_k=5)
    assert len(compact) == 6 and compact["OTHER"] > 0
    drift = compare_categorical({"OK": 90, "FAIL": 10, "OTHER": 0}, {"OK": 0, "FAIL": 10, "NEW": 90, "OTHER": 0})
    assert drift.dominant_appeared == ("NEW",)
    assert drift.dominant_disappeared == ("OK",)


def test_histogram_shape_mismatch_rejected():
    with pytest.raises(ValueError):
        compare_numerical(profile(), profile((1, 2)))
