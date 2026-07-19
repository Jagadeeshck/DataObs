from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

WEIGHTS = {
    "temporal_proximity": 0.18,
    "lineage_distance": 0.16,
    "evidence_strength": 0.18,
    "historical_recurrence": 0.08,
    "change_novelty": 0.08,
    "incident_compatibility": 0.12,
    "downstream_impact": 0.07,
    "business_criticality": 0.05,
    "source_reliability": 0.08,
    "contradictions": -0.20,
}


@dataclass(frozen=True)
class RankingResult:
    score: float
    breakdown: dict[str, float]


def rank(factors: Mapping[str, float]) -> RankingResult:
    normalized = {name: min(1.0, max(0.0, float(factors.get(name, 0.0)))) for name in WEIGHTS}
    breakdown = {name: round(value * WEIGHTS[name], 4) for name, value in normalized.items()}
    return RankingResult(round(min(1.0, max(0.0, sum(breakdown.values()))), 4), breakdown)
