from __future__ import annotations

import math
from statistics import median
from typing import Sequence


def quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * min(1.0, max(0.0, q))
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def median_absolute_deviation(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    center = median(values)
    return median(abs(value - center) for value in values)


def iqr(values: Sequence[float]) -> float:
    return quantile(values, 0.75) - quantile(values, 0.25)


def ewma(values: Sequence[float], alpha: float = 0.3) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def bounded_robust_z_score(value: float, values: Sequence[float], bound: float = 20.0) -> float:
    center = median(values)
    mad = median_absolute_deviation(values)
    if mad == 0:
        return 0.0 if value == center else (bound if value > center else -bound)
    return max(-bound, min(bound, 0.6745 * (value - center) / mad))


def categorical_divergence(current: dict[str, float], expected: dict[str, float]) -> float:
    """Bounded Jensen-Shannon divergence; category values are counts or proportions."""
    keys = set(current) | set(expected)
    ctotal, etotal = sum(current.values()), sum(expected.values())
    if ctotal <= 0 or etotal <= 0:
        return 1.0
    cp = {k: current.get(k, 0) / ctotal for k in keys}
    ep = {k: expected.get(k, 0) / etotal for k in keys}
    midpoint = {k: (cp[k] + ep[k]) / 2 for k in keys}

    def kl(left: dict[str, float], right: dict[str, float]) -> float:
        return sum(left[k] * math.log2(left[k] / right[k]) for k in keys if left[k] > 0)

    return (kl(cp, midpoint) + kl(ep, midpoint)) / 2


def histogram_divergence(current: Sequence[float], expected: Sequence[float]) -> float:
    if len(current) != len(expected):
        raise ValueError("histograms must have identical buckets")
    return categorical_divergence(
        {str(i): v for i, v in enumerate(current)}, {str(i): v for i, v in enumerate(expected)}
    )
