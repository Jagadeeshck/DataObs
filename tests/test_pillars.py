from src.core.pillars import CapabilityStatus, Pillar, score_pillar


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
