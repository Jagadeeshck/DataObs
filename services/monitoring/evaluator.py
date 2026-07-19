from __future__ import annotations

from packages.domain_model.monitor import ColdStartState, MonitorThresholdPolicy, ThresholdMode
from services.monitoring.thresholding import ExpectedRange


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
