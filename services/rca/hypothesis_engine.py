from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from .hypothesis_rules import HypothesisType
from .ranking import rank


class EvidenceRef(BaseModel):
    source_document_ref: str
    summary: str
    strength: float = Field(ge=0, le=1)


class Hypothesis(BaseModel):
    type: HypothesisType
    title: str
    description: str
    suspected_entity: str
    time_relationship: str
    supporting_evidence: List[EvidenceRef] = Field(default_factory=list)
    contradicting_evidence: List[EvidenceRef] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    confidence: float
    impact: str
    rank: int = 0
    deterministic_rule_ids: List[str] = Field(default_factory=list)
    investigation_links: List[str] = Field(default_factory=list)
    recommended_next_check: str
    safe_action_candidates: List[str] = Field(default_factory=list)
    classification: Literal[
        "probable_root_cause",
        "contributing_factor",
        "symptom",
        "correlated_event",
        "insufficient_evidence",
        "ruled_out",
    ] = "insufficient_evidence"
    score_breakdown: Dict[str, float] = Field(default_factory=dict)


def score_hypotheses(candidates: List[tuple[Hypothesis, Dict[str, float]]]) -> List[Hypothesis]:
    scored: list[Hypothesis] = []
    for hypothesis, factors in candidates:
        result = rank(factors)
        hypothesis.confidence = result.score
        hypothesis.score_breakdown = result.breakdown
        scored.append(hypothesis)
    scored.sort(key=lambda item: (-item.confidence, item.type.value, item.suspected_entity))
    for position, hypothesis in enumerate(scored, 1):
        hypothesis.rank = position
        # Ranking is not confirmation. Classification remains rule/evidence controlled.
    return scored
