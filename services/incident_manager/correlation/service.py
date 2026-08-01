from __future__ import annotations

from datetime import datetime, timezone

from packages.domain_model.incident import Incident, deterministic_id

from .contracts import CorrelationDecision, EvidenceState
from .features import extract_features
from .policy import V1_POLICY, CorrelationPolicy
from .scoring import score


class CorrelationService:
    def __init__(self, policy: CorrelationPolicy = V1_POLICY) -> None:
        self.policy = policy

    def evaluate(self, incident: Incident, candidate: Incident, *, revision: str) -> CorrelationDecision:
        p = self.policy
        decision_id = deterministic_id(
            "correlation-decision", [incident.tenant_id, incident.environment, incident.id, revision, p.version]
        )
        if (incident.tenant_id, incident.environment) != (candidate.tenant_id, candidate.environment):
            action, reasons, group_id = "reject", ("scope_incompatible",), None
            features, total, confidence = (), 0.0, 0.0
        else:
            raw = extract_features(incident, candidate)[: p.maximum_features]
            if incident.last_observed_at and candidate.last_observed_at:
                delta = abs((incident.last_observed_at - candidate.last_observed_at).total_seconds())
                if delta > p.correlation_window_seconds:
                    raw = tuple(
                        (
                            type(f)(f.name, EvidenceState.NOT_MATCHED, f.values, f.contribution)
                            if f.name == "temporal_proximity"
                            else f
                        )
                        for f in raw
                    )
            total, confidence, features = score(raw, p)
            coverage = sum(
                f.state not in {EvidenceState.UNAVAILABLE, EvidenceState.UNSUPPORTED} for f in features
            ) / max(len(features), 1)
            enough = coverage >= p.minimum_evidence_coverage
            if not enough:
                confidence = 0.0
            action = (
                "attach"
                if enough and total >= p.minimum_score
                else ("insufficient_evidence" if not enough else "below_threshold")
            )
            reasons = tuple(f.name for f in features if f.state == EvidenceState.MATCHED) or (action,)
            group_id = (
                deterministic_id(
                    "correlation-group",
                    [incident.tenant_id, incident.environment, *sorted([incident.id, candidate.id]), p.version],
                )
                if action == "attach"
                else None
            )
        missing = tuple(f.name for f in features if f.state == EvidenceState.UNAVAILABLE)
        return CorrelationDecision(
            decision_id,
            action,
            incident.id,
            group_id,
            p.name,
            p.version,
            p.canonical_hash,
            datetime.now(timezone.utc),
            total,
            confidence,
            features,
            reasons,
            missing,
        )
