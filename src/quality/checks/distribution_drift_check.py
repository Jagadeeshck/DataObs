"""
Distribution drift detection with dynamic, self-calibrating thresholds.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/24
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

from opentelemetry import metrics, trace

from src.quality.checks.base import BaseCheck, CheckResult

_tracer = trace.get_tracer("dataobs.quality.drift")
_meter = metrics.get_meter("dataobs.quality.drift")

_drift_score_gauge = _meter.create_gauge(
    "dataobs.quality.drift.score",
    description="Current distribution drift score for a column",
    unit="1",
)
_drift_detected_counter = _meter.create_counter(
    "dataobs.quality.drift.detected",
    description="Number of drift threshold breaches detected",
    unit="{breach}",
)


@dataclass
class DriftBaseline:
    """Rolling statistical baseline for a single column."""

    column: str
    table: str
    mean: float = 0.0
    std: float = 0.0
    q1: float = 0.0
    q3: float = 0.0
    null_rate: float = 0.0
    sample_count: int = 0
    bucket_counts: list[int] = field(default_factory=list)
    bucket_edges: list[float] = field(default_factory=list)


class DistributionDriftCheck(BaseCheck):
    """
    Checks for statistical distribution drift in a numeric column.

    Uses Z-score comparison against a rolling baseline. When an
    Elasticsearch baseline store is available, thresholds are computed
    dynamically from historical variance.

    Args:
        table: Table or dataset name.
        column: Column to monitor.
        z_score_threshold: Number of standard deviations to flag as drift.
            Defaults to 3.0; auto-tightened when ES baseline has low variance.
        baseline_store: Optional ElasticsearchBaselineStore for dynamic thresholds.
        null_rate_threshold: Max allowed null rate increase (0–1).
    """

    check_type = "distribution_drift"

    def __init__(
        self,
        table: str,
        column: str,
        z_score_threshold: float = 3.0,
        baseline_store: Any = None,
        null_rate_threshold: float = 0.1,
    ) -> None:
        self.table = table
        self.column = column
        self.z_score_threshold = z_score_threshold
        self.baseline_store = baseline_store
        self.null_rate_threshold = null_rate_threshold

    # ------------------------------------------------------------------
    def run(self, data: list[Optional[float]]) -> CheckResult:  # type: ignore[override]
        """
        Args:
            data: List of column values for the current batch. None = null.

        Returns:
            CheckResult with drift score in metadata.
        """
        with _tracer.start_as_current_span(
            "distribution_drift_check",
            attributes={
                "db.sql.table": self.table,
                "column.name": self.column,
                "check.method": "z_score",
            },
        ) as span:
            values = [v for v in data if v is not None]
            null_count = len(data) - len(values)
            null_rate = null_count / max(len(data), 1)

            if len(values) < 2:
                result = CheckResult(
                    status="skipped",
                    message=f"Insufficient non-null values ({len(values)}) for drift check.",
                    metadata={"null_rate": null_rate},
                )
                span.set_attribute("check.status", "skipped")
                return result

            current_mean = statistics.mean(values)
            current_std = statistics.stdev(values)

            baseline = self._load_or_build_baseline(values, null_rate)
            threshold = self._calibrate_threshold(baseline)

            drift_score = self._z_score(current_mean, baseline.mean, baseline.std)
            null_drift = abs(null_rate - baseline.null_rate)

            attrs = {
                "db.sql.table": self.table,
                "column.name": self.column,
                "check.method": "z_score",
            }

            _drift_score_gauge.set(drift_score, attrs)
            span.set_attribute("drift.score", drift_score)
            span.set_attribute("drift.threshold", threshold)
            span.set_attribute("baseline.mean", baseline.mean)
            span.set_attribute("current.mean", current_mean)

            breached = drift_score > threshold or null_drift > self.null_rate_threshold

            if breached:
                _drift_detected_counter.add(1, attrs)
                span.add_event(
                    "drift_detected",
                    {
                        "drift.score": drift_score,
                        "threshold": threshold,
                        "baseline.mean": baseline.mean,
                        "current.mean": current_mean,
                        "null_drift": null_drift,
                    },
                )

            self._update_baseline(baseline, values, null_rate)

            return CheckResult(
                status="failed" if breached else "passed",
                message=(
                    f"Drift score {drift_score:.3f} exceeds threshold {threshold:.3f}"
                    if breached
                    else f"No drift detected (score={drift_score:.3f})"
                ),
                metadata={
                    "drift_score": drift_score,
                    "threshold": threshold,
                    "baseline_mean": baseline.mean,
                    "current_mean": current_mean,
                    "current_std": current_std,
                    "null_rate": null_rate,
                    "null_drift": null_drift,
                },
            )

    # ------------------------------------------------------------------
    def _load_or_build_baseline(
        self, values: list[float], null_rate: float
    ) -> DriftBaseline:
        if self.baseline_store:
            stored = self.baseline_store.get(self.table, self.column)
            if stored:
                return stored

        # Cold start — build bootstrap baseline from current batch
        return DriftBaseline(
            column=self.column,
            table=self.table,
            mean=statistics.mean(values),
            std=statistics.stdev(values) if len(values) > 1 else 0.0,
            null_rate=null_rate,
            sample_count=len(values),
        )

    def _calibrate_threshold(self, baseline: DriftBaseline) -> float:
        """Tighten threshold when baseline has low variance (stable column)."""
        if baseline.std < 0.01 and baseline.sample_count > 100:
            return max(1.5, self.z_score_threshold * 0.5)
        return self.z_score_threshold

    def _z_score(self, current: float, baseline_mean: float, baseline_std: float) -> float:
        if baseline_std == 0:
            return 0.0 if math.isclose(current, baseline_mean) else float("inf")
        return abs(current - baseline_mean) / baseline_std

    def _update_baseline(
        self, baseline: DriftBaseline, values: list[float], null_rate: float
    ) -> None:
        if self.baseline_store:
            alpha = 0.1  # exponential moving average smoothing
            baseline.mean = (1 - alpha) * baseline.mean + alpha * statistics.mean(values)
            baseline.std = max(
                (1 - alpha) * baseline.std
                + alpha * (statistics.stdev(values) if len(values) > 1 else 0.0),
                1e-9,
            )
            baseline.null_rate = (1 - alpha) * baseline.null_rate + alpha * null_rate
            baseline.sample_count += len(values)
            self.baseline_store.put(baseline)
