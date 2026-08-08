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


class ResourceKind(str, Enum):
    STREAM = "stream"
    TOPIC = "topic"
    QUEUE = "queue"
    EXCHANGE = "exchange"
    SUBSCRIPTION = "subscription"
    CONSUMER_GROUP = "consumer_group"
    SHARD = "shard"
    PARTITION = "partition"
    NAMESPACE = "namespace"
    BROKER = "broker"
    CONNECTOR = "connector"
    DEAD_LETTER_QUEUE = "dead_letter_queue"
    DEAD_LETTER_TOPIC = "dead_letter_topic"


class MeasurementMethod(str, Enum):
    PROVIDER_MEASURED = "provider_measured"
    PROVIDER_APPROXIMATE = "provider_approximate"
    OFFSET_DERIVED = "offset_derived"
    CHECKPOINT_DERIVED = "checkpoint_derived"
    TRACE_DERIVED = "trace_derived"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class LagSemanticType(str, Enum):
    OFFSET_LAG = "offset_lag"
    SEQUENCE_LAG = "sequence_lag"
    TIME_LAG = "time_lag"
    ITERATOR_AGE = "iterator_age"


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


class _Facet(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KafkaFacet(_Facet):
    cleanup_policy: list[str] = Field(default_factory=list, max_length=8)
    replication_factor: int | None = Field(default=None, ge=1)


class KinesisFacet(_Facet):
    stream_mode: Literal["on_demand", "provisioned", "unknown"] = "unknown"
    stream_status: str | None = Field(default=None, max_length=64)
    shard_count: int | None = Field(default=None, ge=0)
    open_shards: int | None = Field(default=None, ge=0)
    closed_shards: int | None = Field(default=None, ge=0)


class SqsFacet(_Facet):
    fifo: bool = False
    content_based_deduplication: bool | None = None
    visibility_timeout_seconds: int | None = Field(default=None, ge=0)
    delay_seconds: int | None = Field(default=None, ge=0)
    encrypted: bool | None = None


class RabbitMqFacet(_Facet):
    vhost: str | None = Field(default=None, max_length=256)
    durable: bool | None = None
    exclusive: bool | None = None
    auto_delete: bool | None = None
    queue_type: Literal["classic", "quorum", "stream", "unknown"] | None = None
    message_ttl_ms: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)
    dead_letter_exchange: str | None = Field(default=None, max_length=512)


class GooglePubSubFacet(_Facet):
    ack_deadline_seconds: int | None = Field(default=None, ge=0)
    exactly_once_delivery: bool | None = None
    ordering_enabled: bool | None = None
    expiration_seconds: int | None = Field(default=None, ge=0)


class AzureEventHubsFacet(_Facet):
    partition_count: int | None = Field(default=None, ge=0)
    capture_enabled: bool | None = None
    status: str | None = Field(default=None, max_length=64)


class AzureServiceBusFacet(_Facet):
    entity_type: Literal["queue", "topic", "subscription", "dead_letter_subqueue"]
    sessions_enabled: bool | None = None
    duplicate_detection_enabled: bool | None = None


class PulsarFacet(_Facet):
    tenant: str | None = Field(default=None, max_length=256)
    persistent: bool | None = None
    partitioned: bool | None = None


class MessagingNamespace(StreamModel):
    provider: str
    provider_account_scope: str
    cloud_region_or_location: str
    provider_resource_id: str
    canonical_resource_id: str
    name: str


class MessagingResource(StreamModel):
    provider: str
    provider_account_scope: str
    cloud_region_or_location: str
    resource_kind: ResourceKind
    provider_resource_id: str = Field(min_length=1, max_length=2048)
    canonical_resource_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=512)
    namespace_id: str | None = None
    parent_resource_id: str | None = None
    kafka: KafkaFacet | None = None
    kinesis: KinesisFacet | None = None
    sqs: SqsFacet | None = None
    rabbitmq: RabbitMqFacet | None = None
    google_pubsub: GooglePubSubFacet | None = None
    azure_event_hubs: AzureEventHubsFacet | None = None
    azure_service_bus: AzureServiceBusFacet | None = None
    pulsar: PulsarFacet | None = None


class MessagingShard(StreamModel):
    resource_id: str
    provider_resource_id: str
    resource_kind: Literal[ResourceKind.SHARD, ResourceKind.PARTITION]
    state: str | None = None


class MessagingSubscription(StreamModel):
    resource_id: str
    provider_resource_id: str
    name: str
    dead_letter_resource_id: str | None = None


class MessagingApplication(StreamModel):
    resource_id: str
    service_name: str
    service_namespace: str | None = None
    role: Literal["producer", "consumer"]
    identity_confidence: Literal["observed", "strongly_correlated", "weakly_correlated", "declared", "unknown"]
    trace_coverage: float = Field(default=0, ge=0, le=1)


class MessagingRoute(StreamModel):
    source_resource_id: str
    destination_resource_id: str
    provider: str
    resource_kind: ResourceKind
    namespace_id: str | None = None
    subscription_or_group_id: str | None = None


class MessagingBacklog(StreamModel):
    resource_id: str
    subscription_id: str | None = None
    backlog_messages: int | None = Field(default=None, ge=0)
    backlog_bytes: int | None = Field(default=None, ge=0)
    backlog_age_seconds: float | None = Field(default=None, ge=0)
    inflight_messages: int | None = Field(default=None, ge=0)
    delayed_messages: int | None = Field(default=None, ge=0)
    unacknowledged_messages: int | None = Field(default=None, ge=0)
    provider_metric: str | None = None
    measurement_method: MeasurementMethod
    semantic_type: str = "backlog"
    unit: str | None = None
    missing_inputs: list[str] = Field(default_factory=list)


class MessagingLag(StreamModel):
    resource_id: str
    subscription_id: str | None = None
    value: float | None = Field(default=None, ge=0)
    semantic_type: LagSemanticType
    provider_metric: str | None = None
    unit: str
    measurement_method: MeasurementMethod
    unavailable_reason: str | None = None
    missing_inputs: list[str] = Field(default_factory=list)


class MessagingRetention(StreamModel):
    resource_id: str
    retention_seconds: float | None = Field(default=None, ge=0)
    retention_bytes: int | None = Field(default=None, ge=0)
    method: str
    evidence_type: str
    missing_inputs: list[str] = Field(default_factory=list)


class MessagingDeadLetterState(StreamModel):
    source_resource_id: str
    dead_letter_resource_id: str
    relationship_type: str
    backlog_count: int | None = Field(default=None, ge=0)
    oldest_item_age: float | None = Field(default=None, ge=0)
    growth_rate: float | None = None


class MessagingThroughput(StreamModel):
    resource_id: str
    incoming_messages_per_second: float | None = Field(default=None, ge=0)
    outgoing_messages_per_second: float | None = Field(default=None, ge=0)
    incoming_bytes_per_second: float | None = Field(default=None, ge=0)
    outgoing_bytes_per_second: float | None = Field(default=None, ge=0)
    provider_metrics: list[str] = Field(default_factory=list)


class MessagingLatency(StreamModel):
    resource_id: str
    value_ms: float | None = Field(default=None, ge=0)
    method: Literal["trace_derived", "provider_estimate", "unavailable"]


class MessagingAvailability(StreamModel):
    resource_id: str
    available: bool | None = None
    state: str
    reasons: list[str] = Field(default_factory=list)


class MessagingDeliveryHealth(StreamModel):
    resource_id: str
    retry_rate: float | None = Field(default=None, ge=0)
    redelivery_rate: float | None = Field(default=None, ge=0)
    throttling_rate: float | None = Field(default=None, ge=0)
    server_error_rate: float | None = Field(default=None, ge=0)


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
