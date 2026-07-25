"""Security boundary shared by observation providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class CapabilityState(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    NOT_CONFIGURED = "not_configured"
    PERMISSION_LIMITED = "permission_limited"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ProviderBudget:
    timeout_seconds: float = 10
    maximum_queries: int = 1
    maximum_scanned_metadata_documents: int = 10_000
    maximum_result_size: int = 100
    maximum_provider_calls: int = 1
    maximum_response_bytes: int = 64_000

    def __post_init__(self) -> None:
        if (
            min(
                self.timeout_seconds,
                self.maximum_queries,
                self.maximum_scanned_metadata_documents,
                self.maximum_result_size,
                self.maximum_provider_calls,
                self.maximum_response_bytes,
            )
            <= 0
        ):
            raise ValueError("provider budgets must be positive")


@dataclass(frozen=True)
class ProviderResult:
    capability: CapabilityState
    value: float | None = None
    sample_count: int = 0
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_coverage: float = 0.0
    confidence: float = 0.0
    missing_data: bool = False
    missing_inputs: tuple[str, ...] = ()
    dimensions: dict[str, str] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def provider_status(self) -> str:
        return self.capability.value


class ObservationProvider(Protocol):
    def validate(self, target: dict[str, Any], budget: ProviderBudget) -> CapabilityState: ...
    def observe(
        self, tenant_id: str, environment: str, target: dict[str, Any], budget: ProviderBudget
    ) -> ProviderResult: ...
