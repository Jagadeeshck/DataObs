from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.data_product import DataProductSLODefinition
from services.data_products.dependencies import reject_cycles, traverse
from services.data_products.reliability import calculate_reliability
from services.data_products.slo_evaluator import evaluate_slo


def slo() -> DataProductSLODefinition:
    return DataProductSLODefinition(
        id="fresh",
        product_id="p",
        tenant_id="t",
        environment="prod",
        component="freshness",
        objective=0.99,
        window="24h",
        evaluation_method="ratio",
        source_monitor_ids=["m"],
        etag='"x"',
    )


def test_missing_slo_evidence_never_passes():
    now = datetime.now(timezone.utc)
    result = evaluate_slo(
        slo(),
        window_start=now - timedelta(days=1),
        window_end=now - timedelta(seconds=1),
        actual_value=1,
        denominator=1,
        evidence_refs=[],
        now=now,
    )
    assert result.state == "source_unavailable"


def test_dependency_order_is_deterministic_and_cycles_fail():
    assert traverse({"a": {"c", "b"}, "b": {"d"}}, "a").nodes == ("b", "c", "d")
    with pytest.raises(ValueError, match="cycle"):
        reject_cycles({"a": {"b"}, "b": {"a"}})


def test_stale_evidence_cannot_improve_reliability():
    baseline = calculate_reliability(
        {"freshness": 0.5, "quality": 1}, {"freshness": 1, "quality": 1}, observed_period="7d"
    )
    stale = calculate_reliability(
        {"freshness": 0.5, "quality": 1}, {"freshness": 1, "quality": 1}, observed_period="7d", stale={"quality"}
    )
    assert stale.overall_score <= baseline.overall_score
    assert stale.stale_components == ["quality"]
