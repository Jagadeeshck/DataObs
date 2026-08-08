"""Bounded aggregate-only numerical and categorical distribution drift."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

MAX_HISTOGRAM_BUCKETS = 100
MAX_CATEGORIES = 50
QUANTILES = ("p05", "p25", "p50", "p75", "p95")


@dataclass(frozen=True)
class NumericalProfile:
    count: int
    null_count: int
    quantiles: Mapping[str, float]
    histogram: tuple[float, ...]
    outlier_ratio: float = 0.0

    def __post_init__(self):
        if self.count < 0 or self.null_count < 0 or self.null_count > self.count:
            raise ValueError("invalid profile counts")
        if set(self.quantiles) != set(QUANTILES):
            raise ValueError("p05, p25, p50, p75 and p95 are required")
        if not 1 <= len(self.histogram) <= MAX_HISTOGRAM_BUCKETS or any(x < 0 for x in self.histogram):
            raise ValueError("histogram must contain 1..100 non-negative bounded buckets")
        if not 0 <= self.outlier_ratio <= 1:
            raise ValueError("outlier_ratio must be in [0,1]")

    @property
    def null_rate(self) -> float:
        return self.null_count / self.count if self.count else 0.0


@dataclass(frozen=True)
class DistributionResult:
    js_divergence: float
    psi: float
    quantile_drift: Mapping[str, float]
    outlier_ratio_change: float
    null_rate_change: float
    dominant_appeared: tuple[str, ...] = ()
    dominant_disappeared: tuple[str, ...] = ()


def _probabilities(values: Sequence[float], *, epsilon: float = 1e-9) -> list[float]:
    total = sum(values)
    if total == 0:
        return [1 / len(values)] * len(values)
    adjusted = [v / total + epsilon for v in values]
    normalizer = sum(adjusted)
    return [v / normalizer for v in adjusted]


def jensen_shannon(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("distributions require equal, non-zero bucket counts")
    p, q = _probabilities(left), _probabilities(right)
    midpoint = [(a + b) / 2 for a, b in zip(p, q)]
    divergence = 0.5 * sum(a * math.log(a / m, 2) for a, m in zip(p, midpoint))
    divergence += 0.5 * sum(b * math.log(b / m, 2) for b, m in zip(q, midpoint))
    return max(0.0, min(1.0, divergence))


def population_stability_index(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("distributions require equal, non-zero bucket counts")
    p, q = _probabilities(left), _probabilities(right)
    return min(100.0, max(0.0, sum((b - a) * math.log(b / a) for a, b in zip(p, q))))


def compare_numerical(baseline: NumericalProfile, observed: NumericalProfile) -> DistributionResult:
    if len(baseline.histogram) != len(observed.histogram):
        raise ValueError("histograms must use the same canonical buckets")
    dispersion = max(baseline.quantiles["p75"] - baseline.quantiles["p25"], 1e-9)
    quantile_drift = {key: abs(observed.quantiles[key] - baseline.quantiles[key]) / dispersion for key in QUANTILES}
    return DistributionResult(
        jensen_shannon(baseline.histogram, observed.histogram),
        population_stability_index(baseline.histogram, observed.histogram),
        quantile_drift,
        observed.outlier_ratio - baseline.outlier_ratio,
        observed.null_rate - baseline.null_rate,
    )


def top_k_profile(counts: Mapping[str, int], top_k: int = 20, *, labels_allowed: bool = True) -> dict[str, int]:
    if not 1 <= top_k <= MAX_CATEGORIES:
        raise ValueError("top_k must be in [1,50]")
    if any(v < 0 for v in counts.values()):
        raise ValueError("category counts cannot be negative")
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if not labels_allowed:
        return {"REDACTED": sum(counts.values()), "OTHER": 0}
    result = dict(ordered[:top_k])
    result["OTHER"] = sum(value for _, value in ordered[top_k:])
    return result


def compare_categorical(baseline: Mapping[str, int], observed: Mapping[str, int]) -> DistributionResult:
    keys = sorted(set(baseline) | set(observed))
    if len(keys) > MAX_CATEGORIES + 1:
        raise ValueError("profiles must be reduced with top_k_profile")
    left, right = [baseline.get(k, 0) for k in keys], [observed.get(k, 0) for k in keys]
    left_total, right_total = max(sum(left), 1), max(sum(right), 1)
    appeared = tuple(k for k in keys if baseline.get(k, 0) == 0 and observed.get(k, 0) / right_total >= 0.1)
    vanished = tuple(k for k in keys if observed.get(k, 0) == 0 and baseline.get(k, 0) / left_total >= 0.1)
    return DistributionResult(
        jensen_shannon(left, right), population_stability_index(left, right), {}, 0.0, 0.0, appeared, vanished
    )
