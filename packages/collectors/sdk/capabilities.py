from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .errors import UnsupportedCapabilityError


class Capability(StrEnum):
    RESOURCE_DISCOVERY = "resource_discovery"
    METADATA_COLLECTION = "metadata_collection"
    METRIC_COLLECTION = "metric_collection"
    LOG_COLLECTION = "log_collection"
    LINEAGE_COLLECTION = "lineage_collection"
    COST_COLLECTION = "cost_collection"
    QUERY_HISTORY = "query_history"
    SCHEMA_DISCOVERY = "schema_discovery"
    HEALTH_CHECK = "health_check"
    INCREMENTAL_COLLECTION = "incremental_collection"
    EVENT_DRIVEN_COLLECTION = "event_driven_collection"


class CollectionMode(StrEnum):
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"
    EVENT_DRIVEN = "event_driven"


@dataclass(frozen=True)
class ProviderCapabilities:
    supported: frozenset[Capability]
    unsupported: frozenset[Capability] = field(default_factory=frozenset)
    required_permissions: tuple[str, ...] = ()
    collection_modes: frozenset[CollectionMode] = field(
        default_factory=lambda: frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND})
    )
    optional_dependencies: tuple[str, ...] = ()
    evidence_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        overlap = self.supported & self.unsupported
        if overlap:
            raise ValueError(f"capabilities cannot be both supported and unsupported: {sorted(overlap)}")

    def require(self, requested: frozenset[Capability]) -> None:
        missing = requested - self.supported
        if missing:
            raise UnsupportedCapabilityError(f"unsupported capabilities: {', '.join(sorted(missing))}")
