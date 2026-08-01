from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class EvidenceState(StrEnum):
    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    STALE = "stale"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class FeatureResult:
    name: str
    state: EvidenceState
    values: tuple[str, ...] = ()
    contribution: float = 0.0


@dataclass(frozen=True)
class CorrelationDecision:
    decision_id: str
    action: str
    incident_id: str
    group_id: str | None
    policy_name: str
    policy_version: str
    policy_hash: str
    evaluated_at: datetime
    score: float
    confidence: float
    features: tuple[FeatureResult, ...]
    reason_codes: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    wording: str = "Related incidents share evidence; this is not a causal conclusion."


@dataclass
class CorrelationGroup:
    id: str
    tenant_id: str
    environment: str
    policy_version: str
    representative_incident_id: str
    member_incident_ids: list[str]
    total_member_count: int
    total_occurrence_count: int
    first_observed_at: datetime
    last_observed_at: datetime
    highest_severity: str
    confidence: float
    reason_codes: list[str]
    evidence_coverage: float
    members_truncated: bool = False
    flood_state: str = "normal"
    notification_decision: str = "notify"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)
