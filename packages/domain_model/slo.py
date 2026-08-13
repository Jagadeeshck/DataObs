"""Canonical data-reliability SLI, SLO, error-budget, and burn-rate contracts.

These contracts are shared by asset and Data Product reliability.  They classify
canonical evidence; they deliberately do not evaluate monitors or contracts.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import DomainModel, utc_now

FORMULA_VERSION = "data-reliability-v1"


class SLIType(str, Enum):
    FRESHNESS = "freshness"
    QUALITY = "quality"
    COMPLETENESS = "completeness"
    VOLUME = "volume"
    SCHEMA_STABILITY = "schema_stability"
    PIPELINE_SUCCESS = "pipeline_success"
    PIPELINE_TIMELINESS = "pipeline_timeliness"
    CONTRACT_COMPLIANCE = "contract_compliance"
    AVAILABILITY = "availability"


class EvidenceClassification(str, Enum):
    GOOD = "good"
    BAD = "bad"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


class SLOExclusion(DomainModel):
    category: Literal[
        "planned_maintenance",
        "approved_backfill",
        "known_provider_outage",
        "scheduled_no_data",
        "manual_approved_exclusion",
    ]
    reason: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=200)
    start: datetime
    end: datetime
    source: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def bounded(self):
        if self.start >= self.end:
            raise ValueError("exclusion start must precede end")
        if self.end - self.start > timedelta(days=365):
            raise ValueError("exclusion must not exceed 365 days")
        return self


class DataReliabilitySLODefinition(DomainModel):
    id: str
    tenant_id: str
    environment: str = "default"
    scope_type: Literal["asset", "monitor_group", "job", "data_product"]
    scope_id: str
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    sli_type: SLIType
    objective: float = Field(gt=0, le=1)
    window: str
    window_type: Literal["rolling", "calendar"] = "rolling"
    evaluation_granularity: Literal["5m", "15m", "30m", "1h", "1d"]
    calculation_method: Literal["good_evaluations", "good_checks", "expected_runs"] = "good_evaluations"
    source_monitor_ids: list[str] = Field(default_factory=list, max_length=100)
    source_job_ids: list[str] = Field(default_factory=list, max_length=100)
    source_contract_ids: list[str] = Field(default_factory=list, max_length=100)
    missing_evidence_policy: Literal["exclude", "count_as_bad", "partial"] = "partial"
    backfill_policy: Literal["count", "exclude", "original_event_time"] = "original_event_time"
    exclusions: list[SLOExclusion] = Field(default_factory=list, max_length=100)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"
    owner_team: str
    state: Literal["draft", "active", "disabled", "archived"] = "draft"
    revision: int = Field(default=1, ge=1)
    etag: str
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: str = "v1"

    @field_validator("window")
    @classmethod
    def bounded_window(cls, value: str) -> str:
        import re

        match = re.fullmatch(r"([1-9]\d*)([mhd])", value)
        if not match:
            raise ValueError("window must be a bounded duration")
        amount, unit = int(match.group(1)), match.group(2)
        duration = timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[unit]: amount})
        if not timedelta(hours=1) <= duration <= timedelta(days=365):
            raise ValueError("window must be between 1h and 365d")
        return value

    @model_validator(mode="after")
    def canonical_source(self):
        if not (self.source_monitor_ids or self.source_job_ids or self.source_contract_ids):
            raise ValueError("at least one canonical evidence source is required")
        return self


class IntervalEvidence(DomainModel):
    classification: EvidenceClassification
    evidence_ref: str | None = None
    reason: str | None = None
    observed_at: datetime | None = None


class ErrorBudget(DomainModel):
    status: Literal["available", "unknown", "zero_error_budget"]
    budget_total: float | None = None
    budget_consumed: float | None = None
    budget_remaining: float | None = None
    budget_consumed_percent: float | None = None
    budget_remaining_percent: float | None = None
    reason_code: str | None = None


class BurnSignal(DomainModel):
    short_window_burn: float | None = None
    long_window_burn: float | None = None
    classification: Literal["normal", "elevated", "slow_burn", "fast_burn", "critical_burn", "unknown"]
    reason_codes: list[str] = Field(default_factory=list)
    estimated_exhaustion_at: datetime | None = None
    estimated_time_remaining_seconds: float | None = None
    forecast_confidence: float = Field(default=0, ge=0, le=1)


class DataReliabilitySLOEvaluation(DomainModel):
    id: str
    tenant_id: str
    environment: str
    slo_id: str
    definition_revision: int
    window_start: datetime
    window_end: datetime
    objective: float
    sli_actual: float | None
    expected_intervals: int
    eligible_intervals: int
    good_intervals: int
    bad_intervals: int
    unknown_intervals: int
    excluded_intervals: int
    coverage_ratio: float = Field(ge=0, le=1)
    evidence_status: Literal["available", "partial", "stale", "missing", "unknown", "unavailable", "not_configured"]
    confidence: float = Field(ge=0, le=1)
    budget: ErrorBudget
    burn: BurnSignal
    state: Literal["healthy", "at_risk", "critical", "exhausted", "unknown", "partial"]
    evidence_refs: list[str] = Field(default_factory=list, max_length=1000)
    exclusion_reasons: list[str] = Field(default_factory=list, max_length=100)
    formula_version: str = FORMULA_VERSION
    evaluated_at: datetime


def calculate_error_budget(*, objective: float, eligible: int, bad: int) -> ErrorBudget:
    """Calculate interval budget; undefined values are represented by ``None``."""
    if not 0 < objective <= 1 or eligible <= 0:
        return ErrorBudget(status="unknown", reason_code="no_eligible_intervals")
    allowed = eligible * (1 - objective)
    if allowed == 0:
        return ErrorBudget(
            status="zero_error_budget",
            budget_total=0,
            budget_consumed=float(bad),
            budget_remaining=-float(bad) if bad else 0,
            reason_code="zero_error_budget",
        )
    consumed_ratio = bad / allowed
    return ErrorBudget(
        status="available",
        budget_total=allowed,
        budget_consumed=float(bad),
        budget_remaining=allowed - bad,
        budget_consumed_percent=consumed_ratio,
        budget_remaining_percent=1 - consumed_ratio,
    )


def calculate_burn_rate(*, objective: float, eligible: int, bad: int) -> tuple[float | None, str | None]:
    if eligible <= 0:
        return None, "insufficient_sample"
    budget_fraction = 1 - objective
    if budget_fraction <= 0:
        return None, "zero_error_budget"
    value = (bad / eligible) / budget_fraction
    return (value, None) if math.isfinite(value) else (None, "non_finite")


def classify_multi_window_burn(
    short_burn: float | None,
    long_burn: float | None,
    *,
    critical_threshold: float = 14.4,
    fast_threshold: float = 6,
    slow_threshold: float = 2,
    elevated_threshold: float = 1,
) -> tuple[str, list[str]]:
    """Classify sustained burn; both windows must cross a sustained threshold."""
    if short_burn is None or long_burn is None:
        return "unknown", ["insufficient_multi_window_evidence"]
    lower = min(short_burn, long_burn)
    if lower >= critical_threshold:
        return "critical_burn", ["both_windows_above_critical_threshold"]
    if lower >= fast_threshold:
        return "fast_burn", ["both_windows_above_fast_threshold"]
    if lower >= slow_threshold:
        return "slow_burn", ["both_windows_above_slow_threshold"]
    if max(short_burn, long_burn) >= elevated_threshold:
        return "elevated", ["one_window_above_sustainable_rate"]
    return "normal", []


def evaluate_intervals(
    definition: DataReliabilitySLODefinition,
    intervals: list[IntervalEvidence],
    *,
    window_start: datetime,
    window_end: datetime,
    short_window: list[IntervalEvidence] | None = None,
    long_window: list[IntervalEvidence] | None = None,
    evaluated_at: datetime | None = None,
) -> DataReliabilitySLOEvaluation:
    """Evaluate already-canonical interval evidence without re-running source logic."""
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    if window_start >= window_end or window_end > evaluated_at:
        raise ValueError("evaluation window is invalid or uses future data")
    counts = {kind.value: 0 for kind in EvidenceClassification}
    refs: set[str] = set()
    reasons: set[str] = set()
    for interval in intervals:
        counts[interval.classification] += 1
        if interval.evidence_ref:
            refs.add(interval.evidence_ref)
        if interval.classification == EvidenceClassification.EXCLUDED and interval.reason:
            reasons.add(interval.reason)
    unknown = counts["unknown"]
    bad = counts["bad"] + (unknown if definition.missing_evidence_policy == "count_as_bad" else 0)
    excluded = counts["excluded"] + (unknown if definition.missing_evidence_policy == "exclude" else 0)
    eligible = len(intervals) - excluded - (unknown if definition.missing_evidence_policy == "partial" else 0)
    known = counts["good"] + counts["bad"]
    coverage = known / len(intervals) if intervals else 0
    actual = counts["good"] / eligible if eligible > 0 else None
    budget = calculate_error_budget(objective=definition.objective, eligible=eligible, bad=bad)
    short = short_window if short_window is not None else intervals
    long = long_window if long_window is not None else intervals
    short_rate, short_reason = _burn_for_evidence(definition.objective, short, definition.missing_evidence_policy)
    long_rate, long_reason = _burn_for_evidence(definition.objective, long, definition.missing_evidence_policy)
    classification, reason_codes = classify_multi_window_burn(short_rate, long_rate)
    reason_codes.extend(reason for reason in (short_reason, long_reason) if reason and reason not in reason_codes)
    partial = definition.missing_evidence_policy == "partial" and unknown > 0
    if not intervals or eligible <= 0:
        state, evidence_status = "unknown", "missing"
    elif partial:
        state, evidence_status = "partial", "partial"
    elif budget.status == "zero_error_budget":
        state, evidence_status = ("exhausted" if bad else "healthy"), "available"
    elif budget.budget_remaining_percent is not None and budget.budget_remaining_percent <= 1e-12:
        state, evidence_status = "exhausted", "available"
    elif budget.budget_remaining_percent is not None and budget.budget_remaining_percent < 0.1:
        state, evidence_status = "critical", "available"
    elif budget.budget_remaining_percent is not None and budget.budget_remaining_percent < 0.5:
        state, evidence_status = "at_risk", "available"
    else:
        state, evidence_status = "healthy", "available"
    fingerprint = sha256("\0".join(sorted(refs)).encode()).hexdigest()
    identity = "\0".join(
        (
            definition.tenant_id,
            definition.environment,
            definition.id,
            str(definition.revision),
            window_start.isoformat(),
            window_end.isoformat(),
            FORMULA_VERSION,
            fingerprint,
        )
    )
    return DataReliabilitySLOEvaluation(
        id=sha256(identity.encode()).hexdigest(),
        tenant_id=definition.tenant_id,
        environment=definition.environment,
        slo_id=definition.id,
        definition_revision=definition.revision,
        window_start=window_start,
        window_end=window_end,
        objective=definition.objective,
        sli_actual=actual,
        expected_intervals=len(intervals),
        eligible_intervals=eligible,
        good_intervals=counts["good"],
        bad_intervals=bad,
        unknown_intervals=unknown,
        excluded_intervals=excluded,
        coverage_ratio=coverage,
        evidence_status=evidence_status,
        confidence=coverage if len(intervals) >= 2 else coverage * 0.5,
        budget=budget,
        burn=BurnSignal(
            short_window_burn=short_rate,
            long_window_burn=long_rate,
            classification=classification,
            reason_codes=reason_codes,
        ),
        state=state,
        evidence_refs=sorted(refs),
        exclusion_reasons=sorted(reasons),
        evaluated_at=evaluated_at,
    )


def _burn_for_evidence(
    objective: float, evidence: list[IntervalEvidence], policy: str
) -> tuple[float | None, str | None]:
    bad = sum(item.classification == EvidenceClassification.BAD for item in evidence)
    unknown = sum(item.classification == EvidenceClassification.UNKNOWN for item in evidence)
    excluded = sum(item.classification == EvidenceClassification.EXCLUDED for item in evidence)
    if policy == "count_as_bad":
        bad += unknown
    elif policy in ("exclude", "partial"):
        excluded += unknown
    return calculate_burn_rate(objective=objective, eligible=len(evidence) - excluded, bad=bad)
