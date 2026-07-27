"""
Monte Carlo-style automated anomaly detection on metric histograms.

Uses bootstrap confidence intervals and histogram bucket drift to detect
anomalies in DataObs quality metric time series without manual thresholds.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/30
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from typing import Sequence

from opentelemetry import metrics, trace

_tracer = trace.get_tracer("dataobs.analytics.anomaly")
_meter = metrics.get_meter("dataobs.analytics.anomaly")

_anomaly_score = _meter.create_gauge("dataobs.anomaly.score", description="Continuous anomaly score", unit="1")
_anomaly_detected = _meter.create_counter(
    "dataobs.anomaly.detected", description="Anomaly detection events", unit="{event}"
)


@dataclass
class AnomalyResult:
    metric_name: str
    current_value: float
    expected_low: float
    expected_high: float
    score: float
    is_anomaly: bool
    severity: str  # "LOW", "HIGH", "AUTO"
    message: str


class BootstrapAnomalyDetector:
    """
    Detects anomalies using bootstrap confidence intervals.

    Resamples the historical window N times to build an expected range
    at each time point. Flags values outside the (1-alpha) CI.

    Args:
        window: Historical values to bootstrap from.
        n_bootstrap: Number of bootstrap resamples.
        alpha: Significance level (default 0.05 = 95% CI).
        metric_name: Name used in OTel attributes.
    """

    def __init__(
        self,
        window: list[float],
        n_bootstrap: int = 1000,
        alpha: float = 0.05,
        metric_name: str = "unknown",
    ) -> None:
        self._window = window
        self._n_bootstrap = n_bootstrap
        self._alpha = alpha
        self._metric_name = metric_name
        self._ci_low, self._ci_high = self._compute_ci()

    def _compute_ci(self) -> tuple[float, float]:
        if len(self._window) < 3:
            return (float("-inf"), float("inf"))
        boot_means = sorted(
            statistics.mean(random.choices(self._window, k=len(self._window))) for _ in range(self._n_bootstrap)
        )
        low_idx = int(self._alpha / 2 * self._n_bootstrap)
        high_idx = int((1 - self._alpha / 2) * self._n_bootstrap)
        return boot_means[low_idx], boot_means[min(high_idx, len(boot_means) - 1)]

    def detect(self, current_value: float) -> AnomalyResult:
        with _tracer.start_as_current_span(
            "anomaly.detect",
            attributes={
                "metric.name": self._metric_name,
                "current.value": current_value,
                "ci.low": self._ci_low,
                "ci.high": self._ci_high,
            },
        ) as span:
            is_anomaly = not (self._ci_low <= current_value <= self._ci_high)
            deviation = max(
                0,
                max(self._ci_low - current_value, current_value - self._ci_high)
                / max(abs(self._ci_high - self._ci_low), 1e-9),
            )
            severity = "HIGH" if deviation > 2.0 else "LOW" if deviation > 0 else "AUTO"
            score = min(deviation, 10.0)

            attrs = {"metric.name": self._metric_name}
            _anomaly_score.set(score, attrs)
            if is_anomaly:
                _anomaly_detected.add(1, {**attrs, "severity": severity})

            span.set_attribute("anomaly.detected", is_anomaly)
            span.set_attribute("anomaly.score", score)
            span.set_attribute("anomaly.severity", severity)

            return AnomalyResult(
                metric_name=self._metric_name,
                current_value=current_value,
                expected_low=self._ci_low,
                expected_high=self._ci_high,
                score=score,
                is_anomaly=is_anomaly,
                severity=severity,
                message=(
                    f"Value {current_value:.4f} outside 95% CI " f"[{self._ci_low:.4f}, {self._ci_high:.4f}]"
                    if is_anomaly
                    else "No anomaly detected"
                ),
            )


class HistogramBucketDriftDetector:
    """
    Detects distribution drift by comparing current histogram bucket
    distribution against a rolling baseline using chi-squared test.

    Resolves: https://github.com/Jagadeeshck/DataObs/issues/30
    """

    def __init__(self, baseline_counts: list[int], metric_name: str = "unknown") -> None:
        self._baseline = baseline_counts
        self._metric_name = metric_name
        self._total_baseline = sum(baseline_counts) or 1

    def detect(self, current_counts: list[int]) -> AnomalyResult:
        if len(current_counts) != len(self._baseline):
            raise ValueError("Bucket count mismatch between current and baseline histograms")

        total_current = sum(current_counts) or 1
        chi2 = sum(
            (o / total_current - e / self._total_baseline) ** 2 / max(e / self._total_baseline, 1e-9)
            for o, e in zip(current_counts, self._baseline)
        )
        is_anomaly = chi2 > 15.0  # approximate p=0.001 for common bucket counts
        score = min(chi2 / 15.0, 10.0)
        attrs = {"metric.name": self._metric_name}
        _anomaly_score.set(score, attrs)
        if is_anomaly:
            _anomaly_detected.add(1, {**attrs, "severity": "HIGH" if chi2 > 30.0 else "LOW"})

        return AnomalyResult(
            metric_name=self._metric_name,
            current_value=chi2,
            expected_low=0.0,
            expected_high=15.0,
            score=score,
            is_anomaly=is_anomaly,
            severity="HIGH" if chi2 > 30.0 else "LOW",
            message=f"Chi-squared={chi2:.2f} ({'anomaly' if is_anomaly else 'normal'})",
        )
