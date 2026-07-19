from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from packages.domain_model.monitor import ColdStartState, MonitorBaselinePolicy

from .cold_start import cold_start_state
from .confidence import baseline_confidence
from .seasonality import select_cohort
from .thresholding import ExpectedRange, robust_range


@dataclass(frozen=True)
class BaselineResult:
    expected_range: ExpectedRange | None
    method: str
    sample_count: int
    confidence: float
    cold_start_state: ColdStartState
    seasonal_cohort: str
    seasonal_cohort_reason: str
    missing_inputs: tuple[str, ...]


def build_baseline(values: Sequence[float], policy: MonitorBaselinePolicy, evaluated_at: datetime) -> BaselineResult:
    state = cold_start_state(len(values), policy.minimum_samples)
    cohort = select_cohort(evaluated_at, list(policy.seasonality))
    expected = robust_range(values, policy.method, policy.sensitivity) if len(values) >= 3 else None
    return BaselineResult(
        expected_range=expected,
        method=policy.method,
        sample_count=len(values),
        confidence=baseline_confidence(len(values), policy.minimum_samples),
        cold_start_state=state,
        seasonal_cohort=cohort.key,
        seasonal_cohort_reason=cohort.reason,
        missing_inputs=("sufficient_history",) if state == ColdStartState.COLLECTING else (),
    )
