from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from packages.domain_model.monitor import ColdStartState, MonitorThresholdPolicy, ThresholdMode
from services.monitoring.thresholding import ExpectedRange

SUPPORTED_MONITOR_TYPES = {
    "freshness",
    "volume",
    "schema_change",
    "field_null_rate",
    "field_unique_rate",
    "field_zero_rate",
    "field_negative_rate",
    "field_cardinality",
    "field_distribution",
    "field_range",
    "metric",
    "metric_comparison",
    "validation",
    "custom_sql_aggregate",
    "query_performance",
    "pipeline_duration",
    "pipeline_missing_run",
    "pathway_latency",
    "consumer_lag",
    "retention_risk",
    "throughput",
    "error_rate",
    "dlq_rate",
    "source_availability",
    "collector_health",
}


@dataclass(frozen=True)
class EvaluationDecision:
    state: str
    final_decision: str
    observation: float | None
    expected_minimum: float | None
    expected_maximum: float | None
    fixed_threshold: dict[str, float | None]
    learned_threshold: dict[str, float] | None
    method: str
    sensitivity: str
    baseline_version: str | None
    sample_count: int
    maturity: ColdStartState
    cohort: str | None
    comparison_periods: Sequence[str]
    exclusions: Sequence[str]
    confidence: float
    missing_inputs: Sequence[str]
    reason_codes: Sequence[str]


def evaluate(
    value: float | None,
    threshold: MonitorThresholdPolicy,
    learned: ExpectedRange | None,
    maturity: ColdStartState,
    *,
    method: str,
    sensitivity: str,
    baseline_version: str | None,
    sample_count: int,
    confidence: float,
    cohort: str | None = None,
    comparison_periods: Sequence[str] = (),
    exclusions: Sequence[str] = (),
    suppressed: bool = False,
    source_available: bool = True,
) -> EvaluationDecision:
    fixed = {
        "minimum": threshold.minimum,
        "maximum": threshold.maximum,
        "safety_minimum": threshold.fixed_safety_minimum,
        "safety_maximum": threshold.fixed_safety_maximum,
    }
    learned_value = None if learned is None else {"minimum": learned.minimum, "maximum": learned.maximum}
    if not source_available:
        state, decision, reasons, missing = (
            "source_unavailable",
            "not_evaluated",
            ("SOURCE_UNAVAILABLE",),
            ("observation",),
        )
    elif value is None:
        state, decision, reasons, missing = (
            "insufficient_data",
            "not_evaluated",
            ("MISSING_OBSERVATION",),
            ("observation",),
        )
    else:
        breached = is_breach(value, threshold, learned, maturity)
        state = "suppressed" if suppressed and breached else ("breached" if breached else "passed")
        decision = "breach_suppressed" if suppressed and breached else ("breach" if breached else "pass")
        reasons = ("FIXED_OR_LEARNED_THRESHOLD_BREACHED",) if breached else ("WITHIN_EXPECTED_RANGE",)
        missing = () if learned is not None else ("learned_threshold",)
    return EvaluationDecision(
        state,
        decision,
        value,
        learned.minimum if learned else None,
        learned.maximum if learned else None,
        fixed,
        learned_value,
        method,
        sensitivity,
        baseline_version,
        sample_count,
        maturity,
        cohort,
        comparison_periods,
        exclusions,
        confidence,
        missing,
        reasons,
    )


def is_breach(
    value: float, threshold: MonitorThresholdPolicy, learned: ExpectedRange | None, maturity: ColdStartState
) -> bool:
    fixed = (
        (threshold.minimum is not None and value < threshold.minimum)
        or (threshold.maximum is not None and value > threshold.maximum)
        or (threshold.fixed_safety_minimum is not None and value < threshold.fixed_safety_minimum)
        or (threshold.fixed_safety_maximum is not None and value > threshold.fixed_safety_maximum)
    )
    if threshold.mode == ThresholdMode.FIXED:
        return fixed
    learned_breach = learned is not None and (value < learned.minimum or value > learned.maximum)
    if maturity != ColdStartState.MATURE:
        return fixed  # immature learned evidence never alerts without a safety violation
    if threshold.mode == ThresholdMode.HYBRID:
        return fixed or learned_breach
    return learned_breach
