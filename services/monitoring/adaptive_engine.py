"""Canonical deterministic adaptive anomaly evaluation.

This module composes the existing robust threshold and seasonal foundations.  It
does not schedule work or own storage; the monitor runtime remains authoritative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from statistics import median
from typing import Sequence

from packages.domain_model.monitor import BaselineMode, BaselineState, MonitorBaselinePolicy
from services.monitoring.thresholding import ExpectedRange, robust_range

SENSITIVITY_PARAMETERS = {
    "low": {"mad_multiplier": 5.0, "score_scale": 1.5},
    "medium": {"mad_multiplier": 3.5, "score_scale": 1.0},
    "high": {"mad_multiplier": 2.5, "score_scale": 0.75},
}


@dataclass(frozen=True)
class HistoricalPoint:
    value: float
    observed_at: datetime
    breached: bool = False
    suppressed: bool = False
    backfill: bool = False
    maintenance: bool = False
    stale: bool = False
    complete: bool = True
    operator_excluded: bool = False


@dataclass(frozen=True)
class AdaptiveResult:
    state: BaselineState
    observed_value: float | None
    center: float | None
    expected_lower: float | None
    expected_upper: float | None
    absolute_deviation: float | None
    normalized_deviation: float | None
    anomaly_score: float | None
    confidence: float
    breached: bool
    sample_count: int
    required_sample_count: int
    oldest_sample: datetime | None
    newest_sample: datetime | None
    cohort: str
    cohort_fallback_reason: str | None
    calculation: str
    exclusions: tuple[str, ...]
    warnings: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    baseline_id: str
    generation: int
    trend_direction: str
    trend_strength: float
    expected_trend_contribution: float


def _duration(value: str) -> timedelta:
    unit = value[-1]
    amount = int(value[:-1])
    return timedelta(**{"h": {"hours": amount}, "d": {"days": amount}}[unit])


def _cohort(at: datetime, dimensions: Sequence[str]) -> str:
    parts: list[str] = []
    for dimension in dimensions[:2]:
        if dimension == "hour_of_day":
            parts.append(f"hour={at.hour:02d}")
        elif dimension in {"day_of_week", "weekly"}:
            parts.append(f"dow={at.weekday()}")
        elif dimension == "weekday_weekend":
            parts.append("weekend" if at.weekday() >= 5 else "weekday")
        elif dimension == "custom":
            parts.append("business_calendar=default")
    return "/".join(parts) or "all"


def _eligible(points: Sequence[HistoricalPoint], policy: MonitorBaselinePolicy, now: datetime):
    reasons: list[str] = []
    result: list[HistoricalPoint] = []
    update = policy.update_policy
    for point in sorted(points, key=lambda p: p.observed_at):
        reason = None
        if point.operator_excluded:
            reason = "operator_exclusion"
        elif update.exclude_breaches and point.breached:
            reason = "prior_breach"
        elif update.exclude_suppressed and point.suppressed:
            reason = "suppressed"
        elif update.exclude_backfills and point.backfill:
            reason = "backfill"
        elif update.exclude_maintenance and point.maintenance:
            reason = "maintenance"
        elif update.exclude_stale and point.stale:
            reason = "stale"
        elif update.exclude_incomplete and not point.complete:
            reason = "incomplete_evidence"
        elif point.observed_at > now - _duration(
            policy.training_window.maximum_age if policy.training_window else "90d"
        ):
            result.append(point)
            continue
        else:
            reason = "outside_training_window"
        reasons.append(reason)
    delay = min(update.learning_delay, len(result))
    if delay:
        reasons.extend(["learning_delay"] * delay)
        result = result[:-delay]
    return result[-policy.history_points :], tuple(reasons)


def evaluate_adaptive(
    observed: float | None,
    points: Sequence[HistoricalPoint],
    policy: MonitorBaselinePolicy,
    evaluated_at: datetime,
    *,
    safety_minimum: float | None = None,
    safety_maximum: float | None = None,
    generation: int = 1,
) -> AdaptiveResult:
    cohort = _cohort(evaluated_at, policy.seasonality)
    eligible, exclusions = _eligible(points, policy, evaluated_at)
    seasonal = [p for p in eligible if _cohort(p.observed_at, policy.seasonality) == cohort]
    fallback = None
    if policy.seasonality and len(seasonal) < policy.minimum_samples:
        selected = eligible
        fallback = f"seasonal cohort has {len(seasonal)} samples; broader baseline used"
    else:
        selected = seasonal if policy.seasonality else eligible
    values = [p.value for p in selected]
    enough = len(values) >= policy.minimum_samples
    expected: ExpectedRange | None = robust_range(values, policy.method, policy.sensitivity) if enough else None
    if expected and policy.mode == BaselineMode.HYBRID:
        expected = ExpectedRange(
            max(expected.minimum, safety_minimum) if safety_minimum is not None else expected.minimum,
            min(expected.maximum, safety_maximum) if safety_maximum is not None else expected.maximum,
            expected.calculation + "; constrained by safety bounds",
        )
    center = median(values) if values else None
    absolute = abs(observed - center) if observed is not None and center is not None else None
    width = max((expected.maximum - expected.minimum) / 2, abs(center or 0) * 0.01, 1e-9) if expected else None
    normalized = absolute / width if absolute is not None and width else None
    outside = bool(observed is not None and expected and (observed < expected.minimum or observed > expected.maximum))
    score = min(100.0, max(0.0, (normalized or 0.0) * 35.0)) if expected and observed is not None else None
    confidence = min(1.0, len(values) / policy.minimum_samples)
    if fallback:
        confidence *= 0.75
    recent = values[-min(7, len(values)) :]
    prior = values[-2 * len(recent) : -len(recent)] if recent else []
    contribution = (median(recent) - median(prior)) if prior and len(values) >= 10 else 0.0
    trend = "increasing" if contribution > 0 else "decreasing" if contribution < 0 else "stable"
    trend_strength = abs(contribution) / max(abs(center or 0), 1e-9)
    newest = selected[-1].observed_at if selected else None
    stale = newest is not None and evaluated_at - newest > _duration(policy.stale_after)
    state = (
        BaselineState.DISABLED
        if not policy.enabled
        else BaselineState.STALE if stale else BaselineState.READY if enough else BaselineState.COLLECTING
    )
    fingerprint = sha256(policy.model_dump_json().encode()).hexdigest()[:16]
    identity = sha256(f"{fingerprint}:{cohort}:{generation}".encode()).hexdigest()
    missing = tuple(
        x for x, condition in (("observation", observed is None), ("sufficient_history", not enough)) if condition
    )
    warnings = tuple(x for x in (fallback, "baseline is stale" if stale else None) if x)
    return AdaptiveResult(
        state,
        observed,
        center,
        expected.minimum if expected else None,
        expected.maximum if expected else None,
        absolute,
        normalized,
        score,
        confidence,
        outside and enough,
        len(values),
        policy.minimum_samples,
        selected[0].observed_at if selected else None,
        newest,
        cohort,
        fallback,
        expected.calculation if expected else "collecting eligible history",
        exclusions,
        warnings,
        missing,
        identity,
        generation,
        trend,
        min(1.0, trend_strength),
        contribution,
    )
