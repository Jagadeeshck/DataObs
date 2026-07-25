from __future__ import annotations

from enum import Enum


class HypothesisType(str, Enum):
    UPSTREAM_DATA_ANOMALY = "upstream_data_anomaly"
    SCHEMA_CHANGE = "schema_change"
    QUERY_CHANGE = "query_change"
    FAILED_QUERY = "failed_query"
    MISSING_QUERY = "missing_query"
    ZERO_WRITE_QUERY = "zero_write_query"
    NEW_QUERY = "new_query"
    JOB_FAILURE = "job_failure"
    JOB_DELAY = "job_delay"
    PIPELINE_MISSING_RUN = "pipeline_missing_run"
    DEPLOYMENT_CHANGE = "deployment_change"
    CONFIGURATION_CHANGE = "configuration_change"
    SOURCE_UNAVAILABLE = "source_unavailable"
    COLLECTOR_FAILURE = "collector_failure"
    INFRASTRUCTURE_SATURATION = "infrastructure_saturation"
    KAFKA_CONSUMER_LAG = "kafka_consumer_lag"
    KAFKA_RETENTION_RISK = "kafka_retention_risk"
    KAFKA_PARTITION_HEALTH = "kafka_partition_health"
    CONNECTOR_FAILURE = "connector_failure"
    QUALITY_FAILURE = "quality_failure"
    FRESHNESS_BREACH = "freshness_breach"
    VOLUME_ANOMALY = "volume_anomaly"
    FIELD_DISTRIBUTION_CHANGE = "field_distribution_change"
    LINEAGE_BREAK = "lineage_break"
    OWNERSHIP_OR_OPERATIONAL_GAP = "ownership_or_operational_gap"
    UNKNOWN = "unknown"
