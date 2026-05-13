"""
DataObs — Row Count Check

Detects anomalous row counts using static thresholds or ML-based baselines.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any, List, Optional

import sqlalchemy
from elasticsearch import Elasticsearch
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base import BaseCheck, CheckResult
from .sql import table_name_from_dataset

logger = logging.getLogger(__name__)

class RowCountCheck(BaseCheck):
    check_type = "row_count"

    def __init__(self, es_client: Optional[Elasticsearch] = None):
        self.es = es_client

    def run(self, config: dict, connection: Any) -> CheckResult:
        """
        Config keys:
          dataset: str
          min_rows: int (optional)
          max_rows: int (optional)
          anomaly_detection: bool (optional, requires es_client)
          stddev_threshold: float (optional, default 3.0)
          severity: str
        """
        dataset = config["dataset"]
        min_rows = config.get("min_rows")
        max_rows = config.get("max_rows")
        anomaly_detection = config.get("anomaly_detection", False)
        stddev_threshold = config.get("stddev_threshold", 3.0)
        severity = config.get("severity", "high")

        try:
            table_name = table_name_from_dataset(dataset)

            with connection.connect() as conn:
                result = conn.execute(sqlalchemy.text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar() or 0

            if min_rows is not None and row_count < min_rows:
                return self._fail(
                    dataset=dataset,
                    message=f"Row count {row_count:,} is below minimum {min_rows:,}",
                    severity=severity,
                    metric_value=float(row_count),
                    threshold=float(min_rows),
                    details={"row_count": row_count, "min_rows": min_rows},
                )

            if max_rows is not None and row_count > max_rows:
                return self._fail(
                    dataset=dataset,
                    message=f"Row count {row_count:,} exceeds maximum {max_rows:,}",
                    severity=severity,
                    metric_value=float(row_count),
                    threshold=float(max_rows),
                    details={"row_count": row_count, "max_rows": max_rows},
                )

            if anomaly_detection and self.es:
                anomaly_result = self._anomaly_check(dataset, row_count, stddev_threshold, severity)
                if anomaly_result:
                    return anomaly_result

            return self._pass(
                dataset=dataset,
                message=f"Row count {row_count:,} is within expected range",
                severity=severity,
                metric_value=float(row_count),
                details={"row_count": row_count},
            )

        except ValueError:
            raise
        except Exception as exc:
            logger.exception("Row count check error for %s", dataset)
            return self._error(dataset, exc)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    def _anomaly_check(
        self, dataset: str, current_count: int, stddev_threshold: float, severity: str
    ) -> Optional[CheckResult]:
        """Compare current row count against 30-day rolling baseline.

        Fix: sort, size, and _source are now passed as top-level keyword
        arguments to es.search() rather than being nested inside the query dict,
        which caused them to be silently ignored and anomaly detection to always
        return 0 historical data points.
        """
        try:
            response = self.es.search(
                index="dataobs-quality-results",
                query={
                    "bool": {
                        "must": [
                            {"term": {"dataset.keyword": dataset}},
                            {"term": {"check_type.keyword": "row_count"}},
                            {"term": {"status.keyword": "PASS"}},
                            {"range": {"@timestamp": {"gte": "now-30d"}}},
                        ]
                    }
                },
                sort=[{"@timestamp": {"order": "desc"}}],
                size=60,
                source=["metric_value"],
            )

            historical: List[float] = [
                hit["_source"]["metric_value"]
                for hit in response["hits"]["hits"]
                if hit["_source"].get("metric_value") is not None
            ]

            if len(historical) < 7:
                return None

            mean = statistics.mean(historical)
            stdev = statistics.stdev(historical)

            if stdev == 0:
                return None

            z_score = abs(current_count - mean) / stdev

            if z_score > stddev_threshold:
                return self._fail(
                    dataset=dataset,
                    message=(
                        f"Row count anomaly: {current_count:,} "
                        f"(z-score={z_score:.2f}, threshold={stddev_threshold})"
                    ),
                    severity=severity,
                    metric_value=float(current_count),
                    threshold=stddev_threshold,
                    details={
                        "row_count": current_count,
                        "historical_mean": round(mean, 2),
                        "historical_stdev": round(stdev, 2),
                        "z_score": round(z_score, 4),
                    },
                )
        except Exception as exc:
            logger.warning("Anomaly detection failed for %s: %s", dataset, exc)

        return None
