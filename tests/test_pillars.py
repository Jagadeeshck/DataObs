from src.core.pillars import (
    LEGACY_PILLAR_ALIASES,
    PILLAR_REGISTRY,
    CapabilityStatus,
    Pillar,
    canonical_pillar_value,
    parse_pillar,
    pillar_deprecation,
    score_pillar,
)


def test_six_canonical_pillar_values_and_registry_complete():
    assert [p.value for p in Pillar] == ["platform", "data_pipeline", "data", "finops_cost", "business", "ai_agent"]
    assert set(PILLAR_REGISTRY) == set(Pillar)


def test_legacy_alias_parsing_and_canonical_output():
    assert parse_pillar("full_stack") is Pillar.PLATFORM
    assert parse_pillar("pipeline") is Pillar.DATA_PIPELINE
    assert canonical_pillar_value("full_stack") == "platform"
    assert pillar_deprecation("pipeline") == {"deprecated": "pipeline", "replacement": "data_pipeline"}


def test_score_pillar_returns_percentage_when_capabilities_are_implemented():
    statuses = [
        CapabilityStatus(key="freshness", implemented=True, maturity=1.0),
        CapabilityStatus(key="validation", implemented=True, maturity=0.5),
        CapabilityStatus(key="lineage", implemented=False, maturity=0.0),
    ]
    score = score_pillar(Pillar.DATA, statuses)
    assert score.total_capabilities == 3
    assert score.implemented_capabilities == 2
    assert round(score.percentage, 2) == round((1.0 * 1.2 + 0.5 * 1.0) / (1.2 + 1.0 + 1.2) * 100, 2)
