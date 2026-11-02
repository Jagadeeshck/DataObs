"""
DataObs — ML Anomaly Check

Rule-free anomaly detection backed by native Elasticsearch machine learning.

Unlike the threshold and z-score checks, this check does not require an operator
to define what "normal" looks like. It relies on an Elasticsearch anomaly-detection
job (managed by ``ElasticsearchMLManager``) that learns the baseline of a metric
time series — seasonality, trend, and level — and surfaces records whose
``record_score`` exceeds a severity threshold.

The monitor runtime is responsible for the ML job lifecycle (create on activate,
delete on deactivate). This check only *reads* the anomaly records that the job
has already produced and maps them into the canonical ``CheckResult`` shape so
they flow through the existing finding → incident pipeline unchanged.

Requires an Elasticsearch Enterprise (X-Pack ML) license. When ML is unavailable
the check returns a WARN with an explicit, honest reason rather than a false PASS.

Config keys:
  dataset: str                         — logical dataset name (for the result)
  ml_job_id: str                       — the ES anomaly-detection job id
  record_score_threshold: int          — anomaly score to flag (default 75)
  severity: str                        — severity to assign on anomaly (default high)
"""

from __future__ import annotations

import logging
from typing import Any, Optional, cast

from elasticsearch import Elasticsearch

from src.analytics.elasticsearch_ml import ElasticsearchMLManager

from .base import BaseCheck, CheckResult

logger = logging.getLogger(__name__)

# Map an ES record_score (0-100) to a DataObs severity band.
_SEVERITY_BANDS = ((90, "critical"), (75, "high"), (50, "medium"), (0, "low"))


def severity_for_score(score: float) -> str:
    """Return the DataObs severity band for an ES anomaly record score."""

    for threshold, severity in _SEVERITY_BANDS:
        if score >= threshold:
            return severity
    return "low"


class MLAnomalyCheck(BaseCheck):
    """Read native Elasticsearch ML anomaly records and project them to findings."""

    check_type = "ml_anomaly"

    def __init__(self, es_client: Optional[Elasticsearch] = None):
        self.es = es_client

    def run(self, config: dict, connection: Any) -> CheckResult:
        dataset = config["dataset"]
        job_id = config.get("ml_job_id")
        threshold = int(config.get("record_score_threshold", 75))
        severity_floor = config.get("severity", "high")

        if self.es is None:
            return self._error(dataset, RuntimeError("ml_anomaly checks require an Elasticsearch client"))
        if not job_id:
            return self._error(dataset, ValueError("ml_anomaly checks require a 'ml_job_id' in config"))

        try:
            manager = ElasticsearchMLManager(cast(Elasticsearch, self.es))
            response = manager.get_top_anomalies(job_id, severity_threshold=threshold, size=1)
            hits = response.get("hits", {}).get("hits", [])

            if not hits:
                # No anomaly at or above the threshold is a genuine PASS: the ML job
                # ran and found nothing notable. This is distinct from "no ML job"
                # (ERROR above) and "ML unavailable" (handled by the exception path).
                return self._pass(
                    dataset=dataset,
                    message=f"No anomalies at or above score {threshold} for job {job_id}",
                    severity="low",
                    details={"ml_job_id": job_id, "record_score_threshold": threshold},
                )

            record = hits[0]["_source"]
            score = float(record.get("record_score", 0.0))
            # The model-derived severity never drops below the operator's floor.
            severity = _max_severity(severity_for_score(score), severity_floor)
            actual = record.get("actual", [None])
            typical = record.get("typical", [None])

            return self._fail(
                dataset=dataset,
                message=(f"ML anomaly detected (score={score:.1f}) on {record.get('detector_description', job_id)}"),
                severity=severity,
                metric_value=score,
                threshold=float(threshold),
                details={
                    "ml_job_id": job_id,
                    "record_score": score,
                    "actual": actual,
                    "typical": typical,
                    "timestamp": record.get("timestamp"),
                    "by_field_value": record.get("by_field_value"),
                    "partition_field_value": record.get("partition_field_value"),
                    "detection_mode": "auto",
                },
            )
        except ValueError:
            raise
        except Exception as exc:
            # ML plugin disabled, license missing, or job not yet producing results.
            # Return an honest WARN — never fabricate a PASS when detection could not run.
            logger.warning("ML anomaly check could not read results for %s (job=%s): %s", dataset, job_id, exc)
            return CheckResult(
                check_type=self.check_type,
                dataset=dataset,
                status="WARN",
                severity="medium",
                message=f"ML anomaly detection unavailable for job {job_id}: {exc}",
                details={"ml_job_id": job_id, "reason": str(exc)},
            )


def _max_severity(a: str, b: str) -> str:
    """Return the higher of two severity labels."""

    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return a if order.get(a, 0) >= order.get(b, 0) else b
