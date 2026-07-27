"""Elasticsearch ML helpers for DataObs anomaly detection use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch
else:
    Elasticsearch = Any


@dataclass
class MLJobConfig:
    job_id: str
    description: str
    index_pattern: str
    time_field: str = "@timestamp"
    bucket_span: str = "15m"
    detector_function: str = "high_mean"
    detector_field: str = "age_seconds"
    query_delay: str = "90s"


class ElasticsearchMLManager:
    """Manages native Elasticsearch ML jobs for DataObs signals."""

    def __init__(self, es_client: Elasticsearch):
        self.es = es_client

    def ensure_job(self, config: MLJobConfig) -> None:
        """Create or update an anomaly detection job + datafeed."""

        job_body: Dict[str, Any] = {
            "description": config.description,
            "analysis_config": {
                "bucket_span": config.bucket_span,
                "detectors": [
                    {
                        "function": config.detector_function,
                        "field_name": config.detector_field,
                    }
                ],
                "influencers": ["dataset", "severity", "check_type"],
            },
            "data_description": {"time_field": config.time_field},
        }
        self.es.ml.put_job(job_id=config.job_id, **job_body)

        datafeed_id = f"datafeed-{config.job_id}"
        datafeed_body = {
            "job_id": config.job_id,
            "indices": [config.index_pattern],
            "query_delay": config.query_delay,
            "query": {"bool": {"filter": [{"exists": {"field": config.detector_field}}]}},
        }
        self.es.ml.put_datafeed(datafeed_id=datafeed_id, **datafeed_body)

    def start_job(self, job_id: str, start: str = "now-30d") -> Dict[str, Any]:
        datafeed_id = f"datafeed-{job_id}"
        self.es.ml.open_job(job_id=job_id)
        return self.es.ml.start_datafeed(datafeed_id=datafeed_id, start=start)

    def get_top_anomalies(self, job_id: str, severity_threshold: int = 50, size: int = 20) -> Dict[str, Any]:
        """Return anomaly records above a score threshold."""

        return self.es.search(
            index=".ml-anomalies-*",
            size=size,
            sort=[{"record_score": "desc"}],
            query={
                "bool": {
                    "filter": [
                        {"term": {"job_id": job_id}},
                        {"term": {"result_type": "record"}},
                        {"range": {"record_score": {"gte": severity_threshold}}},
                    ]
                }
            },
        )


DEFAULT_DATAOBS_ML_JOBS = [
    MLJobConfig(
        job_id="dataobs-freshness-age-anomaly",
        description="Detect spikes in data freshness age.",
        index_pattern="dataobs-freshness*",
        detector_field="age_seconds",
        detector_function="high_mean",
    ),
    MLJobConfig(
        job_id="dataobs-quality-rowcount-anomaly",
        description="Detect row count anomalies in data quality scans.",
        index_pattern="dataobs-quality-results*",
        detector_field="row_count",
        detector_function="mean",
    ),
]
