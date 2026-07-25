"""Executable deterministic RCA orchestration without an external model."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from .hypothesis_engine import EvidenceRef, Hypothesis, score_hypotheses
from .hypothesis_rules import HypothesisType


@dataclass(frozen=True)
class Evidence:
    source_type: str
    source_reference: str
    observed_at: datetime
    tenant_id: str
    environment: str
    entity: str
    reliability: float
    redaction_state: str = "metadata_only"
    attributes: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Investigation:
    investigation_id: str
    incident_id: str
    tenant_id: str
    environment: str
    state: str
    hypotheses: Sequence[Hypothesis]


TYPE_MAP = {
    "deployment": HypothesisType.DEPLOYMENT_CHANGE,
    "schema_change": HypothesisType.SCHEMA_CHANGE,
    "failed_query": HypothesisType.FAILED_QUERY,
    "job_failure": HypothesisType.JOB_FAILURE,
    "consumer_lag": HypothesisType.KAFKA_CONSUMER_LAG,
    "retention_risk": HypothesisType.KAFKA_RETENTION_RISK,
    "source_health": HypothesisType.SOURCE_UNAVAILABLE,
}


def investigate(incident_id: str, tenant_id: str, environment: str, evidence: Iterable[Evidence]) -> Investigation:
    items = [item for item in evidence if item.tenant_id == tenant_id and item.environment == environment]
    candidates = []
    for item in items:
        hypothesis_type = TYPE_MAP.get(item.source_type)
        if not hypothesis_type:
            continue
        contradiction = bool(item.attributes.get("contradicts"))
        ref = EvidenceRef(
            source_document_ref=item.source_reference,
            summary=str(item.attributes.get("summary", item.source_type)),
            strength=item.reliability,
        )
        hypothesis = Hypothesis(
            type=hypothesis_type,
            title=hypothesis_type.value.replace("_", " ").title(),
            description="Deterministic hypothesis derived from redacted structured evidence.",
            suspected_entity=item.entity,
            time_relationship=str(item.attributes.get("time_relationship", "unknown")),
            supporting_evidence=[] if contradiction else [ref],
            contradicting_evidence=[ref] if contradiction else [],
            missing_evidence=["independent corroboration"],
            confidence=0,
            impact="incident compatibility requires review",
            deterministic_rule_ids=[f"RCA-{hypothesis_type.value.upper()}"],
            recommended_next_check="request owner review of the referenced metadata",
            safe_action_candidates=["request owner review"],
            classification="insufficient_evidence",
        )
        factors = {
            "evidence_strength": item.reliability,
            "source_reliability": item.reliability,
            "temporal_proximity": float(item.attributes.get("temporal_proximity", 0)),
            "incident_compatibility": float(item.attributes.get("incident_compatibility", 0.5)),
            "contradictions": item.reliability if contradiction else 0,
        }
        candidates.append((hypothesis, factors))
    digest = hashlib.sha256(f"{tenant_id}|{environment}|{incident_id}".encode()).hexdigest()[:24]
    return Investigation(
        f"rca-{digest}", incident_id, tenant_id, environment, "completed", score_hypotheses(candidates)
    )
