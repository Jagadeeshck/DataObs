"""Adapters map canonical evidence states; they never evaluate source rules."""

from packages.domain_model.slo import EvidenceClassification, IntervalEvidence

STATE_MAP = {
    "success": "good",
    "compliant": "good",
    "passed": "good",
    "on_time": "good",
    "failed": "bad",
    "late": "bad",
    "missing_expected": "bad",
    "violated": "bad",
    "stale": "bad",
    "cancelled": "excluded",
    "skipped": "excluded",
    "excluded": "excluded",
    "warning": "unknown",
    "unknown": "unknown",
}


def canonical_interval(*, state: str, evidence_ref: str, observed_at=None) -> IntervalEvidence:
    try:
        classification = EvidenceClassification(STATE_MAP[state])
    except KeyError as exc:
        raise ValueError(f"unsupported canonical evidence state: {state}") from exc
    return IntervalEvidence(classification=classification, evidence_ref=evidence_ref, observed_at=observed_at)
