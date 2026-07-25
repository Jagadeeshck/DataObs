from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MessagingSystem(str, Enum):
    KAFKA = "kafka"
    KINESIS = "kinesis"
    SQS = "sqs"
    RABBITMQ = "rabbitmq"
    GOOGLE_PUBSUB = "google_pubsub"
    PULSAR = "pulsar"
    AZURE_EVENT_HUBS = "azure_event_hubs"
    AZURE_SERVICE_BUS = "azure_service_bus"
    UNKNOWN = "unknown"


class DataStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    STALE = "stale"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class StreamEvidence(BaseModel):
    source: str
    observed_at: datetime
    method: str
    kind: Literal["measured", "derived", "estimated", "declared"]
    reference: str | None = None


class StreamModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    id: str
    tenant_id: str
    environment: str
    messaging_system: MessagingSystem
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_status: DataStatus = DataStatus.UNKNOWN
    source_coverage: float = Field(default=0, ge=0, le=1)
    confidence: float = Field(default=0, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    evidence: list[StreamEvidence] = Field(default_factory=list)
    request_id: str | None = None
    trace_id: str | None = None


class KafkaClusterFacet(BaseModel):
    controller_id: int | None = None
    kraft: bool | None = None


class KafkaTopicFacet(BaseModel):
    cleanup_policy: list[str] = Field(default_factory=list)
    replication_factor: int | None = None


class KafkaPartitionFacet(BaseModel):
    leader_id: int | None = None
    replicas: list[int] = Field(default_factory=list)
    isr: list[int] = Field(default_factory=list)


class KafkaConsumerGroupFacet(BaseModel):
    generation: int | None = None
    coordinator_id: int | None = None
    protocol: str | None = None


class KafkaConnectorFacet(BaseModel):
    worker_id: str | None = None


class KafkaSchemaFacet(BaseModel):
    schema_id: int | None = None
    schema_type: str | None = None


class StreamCluster(StreamModel):
    name: str
    broker_count: int | None = None
    kafka: KafkaClusterFacet | None = None


class StreamBroker(StreamModel):
    cluster_id: str
    broker_id: str
    rack: str | None = None


class StreamResource(StreamModel):
    cluster_id: str
    name: str
    partition_count: int | None = None
    owner_team: str | None = None
    data_product_ids: list[str] = Field(default_factory=list)
    kafka: KafkaTopicFacet | None = None


class StreamPartition(StreamModel):
    stream_id: str
    partition_id: str
    kafka: KafkaPartitionFacet | None = None


class StreamApplication(StreamModel):
    stream_id: str
    service_id: str
    identity_confidence: Literal["observed", "strongly_correlated", "weakly_correlated", "declared", "unknown"]


class ProducerApplication(StreamApplication):
    pass


class ConsumerApplication(StreamApplication):
    group_id: str | None = None


class ConsumerGroup(StreamModel):
    cluster_id: str
    group_id: str
    state: str
    member_count: int | None = None
    kafka: KafkaConsumerGroupFacet | None = None


class ConsumerMember(StreamModel):
    group_id: str
    member_fingerprint: str
    assignments: list[str] = Field(default_factory=list)


class StreamConnector(StreamModel):
    cluster_id: str
    name: str
    connector_type: Literal["source", "sink", "unknown"]
    state: str
    config_fingerprint: str
    kafka: KafkaConnectorFacet | None = None


class ConnectorTask(StreamModel):
    connector_id: str
    task_id: int
    state: str


class StreamSchemaSubject(StreamModel):
    subject: str
    compatibility_mode: str | None = None
    kafka: KafkaSchemaFacet | None = None


class StreamSchemaVersion(StreamModel):
    subject_id: str
    version: int
    fingerprint: str


class StreamConfiguration(StreamModel):
    resource_id: str
    fingerprint: str
    values: dict[str, Any] = Field(default_factory=dict)


class StreamConfigurationChange(StreamModel):
    resource_id: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)


class StreamOffsets(StreamModel):
    stream_id: str
    partition_id: str
    group_id: str
    log_start_offset: int | None = None
    high_watermark: int | None = None
    last_stable_offset: int | None = None
    committed_offset: int | None = None


class StreamLag(StreamModel):
    lag_messages: int | None
    velocity_messages_per_second: float | None = None
    drain_time_seconds: float | None = None
    convergence: Literal["converging", "not_converging", "unknown"] = "unknown"
    method: str
    missing_inputs: list[str] = Field(default_factory=list)


class StreamRetention(StreamModel):
    retention_seconds: float | None = None
    retention_bytes: int | None = None
    cleanup_policy: list[str] = Field(default_factory=list)


class StreamRetentionRisk(StreamModel):
    state: Literal["none", "low", "medium", "high", "critical", "data_loss_suspected", "unknown", "not_applicable"]
    estimated_time_remaining_seconds: float | None = None
    missing_inputs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class StreamReplicationHealth(StreamModel):
    under_replicated: bool | None = None
    offline: bool | None = None
    reasons: list[str] = Field(default_factory=list)


class StreamThroughput(StreamModel):
    messages_per_second: float | None = None
    bytes_per_second: float | None = None


class StreamLatency(StreamModel):
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None


class StreamHealth(StreamModel):
    state: str
    reasons: list[str] = Field(default_factory=list)


class StreamSLO(StreamModel):
    target_id: str
    metric: str
    threshold: float


class StreamActionEligibility(StreamModel):
    action: str
    eligible: bool
    approval_required: bool = True
    reasons: list[str] = Field(default_factory=list)


class StreamActionRequest(StreamModel):
    action: str
    target_id: str
    reason: str
    idempotency_key: str


class StreamActionResult(StreamModel):
    request_id: str
    state: str


class MessageInspectionPolicy(StreamModel):
    enabled: bool = False
    topic_allowlist: list[str] = Field(default_factory=list)
    max_messages: int = Field(default=10, ge=1, le=100)
    max_bytes: int = Field(default=65536, ge=1, le=1048576)


class MessageInspectionRequest(StreamModel):
    stream_id: str
    reason: str
    max_messages: int = Field(ge=1, le=100)


class MessageInspectionResult(StreamModel):
    sampled: bool = True
    persisted_payloads: bool = False
    messages: list[dict[str, Any]] = Field(default_factory=list)
