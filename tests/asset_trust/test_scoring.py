from datetime import datetime, timezone

import pytest

from packages.domain_model.asset_trust import AssetTrustEvidence, AssetTrustPolicy
from services.asset_trust.scoring import attribute_change, calculate_asset_trust, deduplicate_evidence

NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


def ev(dimension, score=95, ref=None, source="canonical_evaluation", **kw):
    return AssetTrustEvidence(
        evidence_source=source, evidence_ref=ref or dimension, dimension=dimension, score=score, observed_at=NOW, **kw
    )


def calculate(evidence, policy=None):
    return calculate_asset_trust(
        tenant_id="t",
        environment="prod",
        asset_id="a",
        evidence=evidence,
        policy=policy or AssetTrustPolicy(policy_id="default", name="Default"),
        window_start=NOW,
        window_end=NOW,
    )


def test_all_strong_is_high_confidence():
    score = calculate([ev(name) for name in AssetTrustPolicy(policy_id="p", name="p").dimension_weights])
    assert (score.score, score.confidence, score.evidence_coverage, score.state) == (95, 1, 1, "strong")


def test_good_score_with_missing_evidence_is_partial_not_zero():
    score = calculate([ev("quality", 96), ev("freshness", 98)])
    assert score.score == pytest.approx(96.857142857)
    assert score.evidence_coverage == 0.35
    assert score.confidence == 0.35
    assert score.state == "partial"
    assert "delivery_reliability" in score.missing_dimensions


def test_all_missing_is_unknown_and_null():
    score = calculate([])
    assert score.score is None and score.state == "unknown" and score.confidence == 0


def test_stale_evidence_reduces_confidence_and_is_not_scored():
    score = calculate([ev("quality", status="stale"), ev("freshness")])
    assert score.score == 95
    assert score.confidence == 0.15
    assert score.stale_dimensions == ["quality"]


def test_slo_precedence_prevents_monitor_double_count():
    evidence = [
        ev("freshness", 20, "monitor:1", derived_from=["monitor:1"]),
        ev("freshness", 90, "slo:1", source="production_slo", derived_from=["monitor:1"]),
    ]
    selected = deduplicate_evidence(evidence)
    assert [(e.evidence_ref, e.score) for e in selected] == [("slo:1", 90)]


def test_critical_cap_is_explainable():
    values = [ev(name) for name in AssetTrustPolicy(policy_id="p", name="p").dimension_weights]
    values[3] = ev("slo_reliability", 90, reason_codes=["slo.budget_exhausted"])
    score = calculate(values)
    assert score.uncapped_score == 94 and score.score == 65
    assert score.cap_applied and score.cap_reason == "slo.budget_exhausted"


def test_policy_rejects_bad_weights_and_unknown_dimensions():
    with pytest.raises(ValueError):
        AssetTrustPolicy(policy_id="p", name="p", dimension_weights={"quality": 0.5})
    weights = AssetTrustPolicy(policy_id="p", name="p").dimension_weights | {"mystery": 0}
    with pytest.raises(ValueError):
        AssetTrustPolicy(policy_id="p", name="p", dimension_weights=weights)


def test_attribution_is_deterministic():
    before = calculate([ev(name, 90) for name in AssetTrustPolicy(policy_id="p", name="p").dimension_weights])
    after_values = [ev(name, 90) for name in AssetTrustPolicy(policy_id="p", name="p").dimension_weights]
    after_values[1] = ev("freshness", 50)
    after = calculate(after_values)
    assert attribute_change(before, after)[0] == {"dimension": "freshness", "contribution": -6.0}
