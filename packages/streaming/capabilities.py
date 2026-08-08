from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CapabilityState(str, Enum):
    NOT_IMPLEMENTED = "not_implemented"
    NOT_CONFIGURED = "not_configured"
    PARTIAL = "partial"
    AVAILABLE = "available"
    FUNCTIONAL = "functional"
    UNSUPPORTED = "unsupported"


class AdapterCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    provider: str
    messaging_system: str | None = None
    state: CapabilityState
    inventory: CapabilityState
    topology: CapabilityState = CapabilityState.NOT_CONFIGURED
    throughput: CapabilityState = CapabilityState.NOT_CONFIGURED
    byte_throughput: CapabilityState = CapabilityState.NOT_CONFIGURED
    backlog_count: CapabilityState = CapabilityState.NOT_CONFIGURED
    backlog_age: CapabilityState = CapabilityState.NOT_CONFIGURED
    offsets: CapabilityState = CapabilityState.UNSUPPORTED
    consumer_groups: CapabilityState = CapabilityState.UNSUPPORTED
    subscriptions: CapabilityState = CapabilityState.UNSUPPORTED
    partitions: CapabilityState = CapabilityState.UNSUPPORTED
    shards: CapabilityState = CapabilityState.UNSUPPORTED
    retention: CapabilityState = CapabilityState.NOT_CONFIGURED
    replication: CapabilityState = CapabilityState.UNSUPPORTED
    availability: CapabilityState = CapabilityState.NOT_CONFIGURED
    dead_letter: CapabilityState = CapabilityState.UNSUPPORTED
    retries: CapabilityState = CapabilityState.NOT_CONFIGURED
    redelivery: CapabilityState = CapabilityState.UNSUPPORTED
    schemas: CapabilityState = CapabilityState.UNSUPPORTED
    connectors: CapabilityState = CapabilityState.UNSUPPORTED
    producer_identity: CapabilityState = CapabilityState.NOT_CONFIGURED
    consumer_identity: CapabilityState = CapabilityState.NOT_CONFIGURED
    otel_trace_correlation: CapabilityState = CapabilityState.NOT_CONFIGURED
    configuration: CapabilityState = CapabilityState.NOT_CONFIGURED
    configuration_changes: CapabilityState = CapabilityState.NOT_CONFIGURED
    limitations: list[str] = Field(default_factory=list)

    @property
    def groups(self) -> CapabilityState:
        """Compatibility alias for the original Kafka-oriented API."""
        return CapabilityState(self.consumer_groups)
