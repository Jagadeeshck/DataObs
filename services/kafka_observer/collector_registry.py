from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

CAPABILITIES = {
    "broker_metrics",
    "topic_metrics",
    "partition_metrics",
    "consumer_group_metrics",
    "client_metrics",
    "configuration_inventory",
    "offset_inventory",
    "schema_registry",
    "kafka_connect",
    "otel_pathways",
    "logs",
}


class CapabilityBinding(BaseModel):
    capability: str
    selected_provider: str
    fallback_provider: str | None = None
    collection_interval_seconds: int = Field(gt=0)
    source_integration_id: str
    source_event_identity: str
    precedence: int = 100
    deduplication_key: str
    last_successful_collection: datetime | None = None
    health: str = "unknown"


def validate_bindings(bindings: list[CapabilityBinding], *, comparison_mode: bool = False) -> None:
    seen: dict[str, str] = {}
    for binding in bindings:
        if binding.capability not in CAPABILITIES:
            raise ValueError(f"unknown capability: {binding.capability}")
        prior = seen.get(binding.capability)
        if prior and prior != binding.selected_provider and not comparison_mode:
            raise ValueError(
                f"conflicting authoritative providers for {binding.capability}: {prior}, {binding.selected_provider}"
            )
        seen[binding.capability] = binding.selected_provider
