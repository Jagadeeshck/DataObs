from services.data_products.reliability import calculate_reliability


def test_missing_evidence_is_excluded_not_healthy():
    result = calculate_reliability(
        {"freshness": 0.8, "quality": None}, {"freshness": 1, "quality": 3}, observed_period="7d"
    )
    assert result.overall_score == 0.8
    assert result.confidence == 0.25
    assert result.missing_components == ["quality"]


def test_no_evidence_is_unknown():
    result = calculate_reliability({"freshness": None}, {"freshness": 1}, observed_period="7d")
    assert result.overall_score is None
    assert result.overall_state == "unknown"
