from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence

from .robust_statistics import median_absolute_deviation, quantile


@dataclass(frozen=True)
class ExpectedRange:
    minimum: float
    maximum: float
    calculation: str


def robust_range(values: Sequence[float], method: str, sensitivity: str) -> ExpectedRange:
    if len(values) < 3:
        raise ValueError("at least three samples are required")
    multiplier = {"low": 5.0, "medium": 3.5, "high": 2.5}[sensitivity]
    center = median(values)
    if method in {"mad", "rolling_median"}:
        spread = median_absolute_deviation(values) * 1.4826
        spread = max(spread, abs(center) * 0.01, 1e-9)
        return ExpectedRange(
            center - multiplier * spread, center + multiplier * spread, f"median ± {multiplier} × scaled MAD"
        )
    if method == "iqr":
        q1, q3 = quantile(values, 0.25), quantile(values, 0.75)
        spread = q3 - q1
        return ExpectedRange(
            q1 - multiplier / 2 * spread, q3 + multiplier / 2 * spread, f"IQR fences with multiplier {multiplier / 2}"
        )
    low, high = quantile(values, 0.05), quantile(values, 0.95)
    return ExpectedRange(low, high, "robust 5th–95th quantiles")
