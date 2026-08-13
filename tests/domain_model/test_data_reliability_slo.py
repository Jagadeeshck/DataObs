from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.slo import (
    DataReliabilitySLODefinition,
    IntervalEvidence,
    calculate_burn_rate,
    calculate_error_budget,
    classify_multi_window_burn,
    evaluate_intervals,
)


def definition(**updates):
    values = dict(
        id="orders-freshness",
        tenant_id="t1",
        scope_type="asset",
        scope_id="orders",
        name="Orders freshness",
        sli_type="freshness",
        objective=0.99,
        window="30d",
        evaluation_granularity="1h",
        source_monitor_ids=["m1"],
        owner_team="orders",
        etag="e1",
        created_by="alice",
    )
    values.update(updates)
    return DataReliabilitySLODefinition(**values)


def evidence(*values):
    return [
        IntervalEvidence(classification=value, evidence_ref=f"monitor:{index}") for index, value in enumerate(values)
    ]


def evaluate(items, **definition_updates):
    now = datetime(2026, 1, 31, tzinfo=timezone.utc)
    return evaluate_intervals(
        definition(**definition_updates), items, window_start=now - timedelta(days=30), window_end=now, evaluated_at=now
    )


@pytest.mark.parametrize(
    "policy,eligible,bad,state",
    [("exclude", 2, 0, "healthy"), ("count_as_bad", 3, 1, "exhausted"), ("partial", 2, 0, "partial")],
)
def test_missing_evidence_policies_are_distinct(policy, eligible, bad, state):
    result = evaluate(evidence("good", "good", "unknown"), missing_evidence_policy=policy)
    assert (result.eligible_intervals, result.bad_intervals, result.state) == (eligible, bad, state)
    assert result.coverage_ratio == pytest.approx(2 / 3)


def test_exact_budget_consumption_and_deterministic_identity():
    items = evidence(*(["good"] * 990), *(["bad"] * 10))
    first = evaluate(items)
    second = evaluate(items)
    assert first.sli_actual == 0.99
    assert first.budget.budget_remaining_percent == pytest.approx(0)
    assert first.state == "exhausted"
    assert first.id == second.id


@pytest.mark.parametrize(
    "objective,eligible,bad,expected",
    [(0.99, 100, 0, 0), (0.99, 100, 1, 1), (0.999, 1000, 10, 10), (0.99, 100, 100, 100)],
)
def test_burn_rate(objective, eligible, bad, expected):
    value, reason = calculate_burn_rate(objective=objective, eligible=eligible, bad=bad)
    assert value == pytest.approx(expected)
    assert reason is None


def test_undefined_numbers_are_null_not_non_finite():
    assert calculate_burn_rate(objective=1, eligible=1, bad=1) == (None, "zero_error_budget")
    assert calculate_error_budget(objective=1, eligible=1, bad=1).budget_remaining == -1
    unknown = calculate_error_budget(objective=0.99, eligible=0, bad=0)
    assert unknown.budget_remaining is None
    assert "Infinity" not in unknown.model_dump_json()


@pytest.mark.parametrize(
    "short,long,expected",
    [
        (0, 0, "normal"),
        (2, 0.5, "elevated"),
        (2, 2, "slow_burn"),
        (6, 8, "fast_burn"),
        (20, 15, "critical_burn"),
        (None, 2, "unknown"),
    ],
)
def test_multi_window_classification(short, long, expected):
    assert classify_multi_window_burn(short, long)[0] == expected


def test_exclusions_are_transparent_and_not_good():
    result = evaluate(
        [IntervalEvidence(classification="good"), IntervalEvidence(classification="excluded", reason="maintenance")]
    )
    assert result.good_intervals == 1
    assert result.excluded_intervals == 1
    assert result.exclusion_reasons == ["maintenance"]


def test_definition_requires_bounded_window_and_canonical_source():
    with pytest.raises(ValueError):
        definition(window="366d")
    with pytest.raises(ValueError):
        definition(source_monitor_ids=[])
