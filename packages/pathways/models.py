from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class NodeType(str, Enum):
    SERVICE = "service"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    KAFKA_CLUSTER = "kafka_cluster"
    BROKER = "broker"
    TOPIC = "topic"
    PARTITION = "partition"
    CONSUMER_GROUP = "consumer_group"
    KAFKA_CONNECT_SOURCE = "kafka_connect_source"
    KAFKA_CONNECT_SINK = "kafka_connect_sink"
    JOB = "job"
    DATASET = "dataset"
    EXTERNAL_SOURCE = "external_source"
    EXTERNAL_SINK = "external_sink"
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    PRODUCER_TO_TOPIC = "producer_to_topic"
    TOPIC_TO_CONSUMER = "topic_to_consumer"
    CONSUMER_INTERNAL = "consumer_internal"
    CONSUMER_TO_TOPIC = "consumer_to_topic"
    CONNECTOR_SOURCE_TO_TOPIC = "connector_source_to_topic"
    TOPIC_TO_CONNECTOR_SINK = "topic_to_connector_sink"
    JOB_TO_TOPIC = "job_to_topic"
    TOPIC_TO_JOB = "topic_to_job"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class PathwayType(str, Enum):
    FULL = "full"
    EDGE = "edge"
    PARTIAL_EDGE = "partial_edge"
    INTERNAL = "internal"
    INFERRED = "inferred"


class CommonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    id: str
    tenant_id: str
    environment: str
    source_integration_id: str
    kafka_cluster_id: str | None = None
    schema_version: str = "v1"
    event_version: str = "v1"
    owner_team: str | None = None
    business_service: str | None = None
    service_namespace: str | None = None
    service_name: str | None = None
    service_version: str | None = None
    cloud_provider: str | None = None
    cloud_region: str | None = None
    timestamp: datetime = Field(default_factory=now)
    observed_timestamp: datetime = Field(default_factory=now)
    ingestion_timestamp: datetime = Field(default_factory=now)
    correlation_id: str | None = None
    trace_id: str | None = None
    data_classification: str = "metadata"
    collection_provider: str = "dataobs_kafka_observer"
    collection_confidence: float = Field(default=1.0, ge=0, le=1)
    lifecycle_state: str = "active"
    evidence: list[str] = Field(default_factory=list)


class PathwayNode(CommonModel):
    node_type: NodeType
    namespace: str = ""
    name: str


class PathwayEdge(CommonModel):
    source_node_id: str
    destination_node_id: str
    edge_type: EdgeType
    messaging_system: str = "kafka"
    topic: str | None = None
    consumer_group: str | None = None


class PathwayDefinition(CommonModel):
    edge_ids: list[str] = Field(default_factory=list)


class PathwayMeasurement(CommonModel):
    pathway_id: str
    source_node_id: str
    destination_node_id: str
    pathway_type: PathwayType
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    throughput_messages_per_second: float = 0
    throughput_bytes_per_second: float = 0
    payload_size_p50_bytes: float = 0
    payload_size_p95_bytes: float = 0
    lag_messages: int | None = None
    lag_seconds: float | None = None
    error_rate: float = 0
    retry_rate: float = 0
    dlq_messages: int = 0
    confidence: float = Field(default=1, ge=0, le=1)


class PathwayHealth(CommonModel):
    state: str
    reasons: list[str] = Field(default_factory=list)


class PathwaySLO(CommonModel):
    slo_type: str
    threshold: float
    enabled: bool = True
    revision: int = 1


class PathwaySLOResult(CommonModel):
    slo_id: str
    value: float
    breached: bool


class RetentionRisk(CommonModel):
    state: str
    time_risk_ratio: float | None = None
    bytes_risk_ratio: float | None = None
    drain_time_seconds: float | None = None
    estimated_data_loss_seconds: float | None = None
    reasons: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)


class StreamFinding(CommonModel):
    finding_type: str
    severity: str
    status: str = "active"
    topic_id: str | None = None
    consumer_group_id: str | None = None
    pathway_id: str | None = None
    reasons: list[str] = Field(default_factory=list)
