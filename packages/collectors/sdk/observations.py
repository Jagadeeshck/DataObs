from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping, TypeAlias

from .checkpoints import CollectionCheckpoint


def canonical_resource_id(provider: str, account: str, region: str, service: str, native_id: str) -> str:
    material = "\x1f".join((provider, account, region, service, native_id)).encode()
    return f"resource:{hashlib.sha256(material).hexdigest()}"


class EvidenceState(StrEnum):
    MEASURED = "measured"
    MISSING = "missing"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    STALE = "stale"
    PARTIAL = "partial"


@dataclass(frozen=True)
class ResourceObservation:
    provider: str
    account: str
    region: str
    service: str
    resource_type: str
    native_resource_id: str
    display_name: str
    observed_at: datetime
    collection_run_id: str
    tags: Mapping[str, str] = field(default_factory=dict)
    owner: str | None = None
    source_evidence: Mapping[str, Any] = field(default_factory=dict)
    evidence_confidence: float | None = None
    canonical_id: str = ""

    def __post_init__(self) -> None:
        if not self.canonical_id:
            object.__setattr__(
                self,
                "canonical_id",
                canonical_resource_id(self.provider, self.account, self.region, self.service, self.native_resource_id),
            )


@dataclass(frozen=True)
class MetricObservation:
    resource_id: str
    metric_name: str
    value: float | None
    state: EvidenceState
    unit: str
    aggregation: str
    period_seconds: int
    timestamp: datetime
    source_provider: str
    dimensions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state == EvidenceState.MEASURED and self.value is None:
            raise ValueError("measured metrics require a value")
        if self.state != EvidenceState.MEASURED and self.value is not None:
            raise ValueError("non-measured metrics cannot carry a value")


@dataclass(frozen=True)
class HealthObservation:
    resource_id: str
    status: str
    reason: str
    evidence: EvidenceState
    severity: str
    observed_at: datetime
    freshness_seconds: int | None = None


@dataclass(frozen=True)
class PartialFailure:
    capability: str
    error_code: str
    message: str
    retryable: bool


ProviderObservation: TypeAlias = ResourceObservation | MetricObservation | HealthObservation | PartialFailure


@dataclass(frozen=True)
class CollectionRunResult:
    run_id: str
    requested_capabilities: frozenset[str]
    completed_capabilities: frozenset[str]
    started_at: datetime
    completed_at: datetime
    discovered_resources: int
    emitted_observations: int
    skipped: int
    partial_failures: tuple[PartialFailure, ...]
    retry_count: int
    checkpoint_before: CollectionCheckpoint | None = None
    checkpoint_after: CollectionCheckpoint | None = None
    observations: tuple[ProviderObservation, ...] = ()
