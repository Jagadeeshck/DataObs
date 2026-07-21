"""Security boundary shared by observation providers."""

from __future__ import annotations

from dataclasses import dataclass, field
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

    def __post_init__(self) -> None:
        if (
            min(
                self.timeout_seconds,
                self.maximum_queries,
                self.maximum_scanned_metadata_documents,
                self.maximum_result_size,
                self.maximum_provider_calls,
            )
            <= 0
        ):
            raise ValueError("provider budgets must be positive")


@dataclass(frozen=True)
class ProviderResult:
    capability: CapabilityState
    value: float | None = None
    missing_inputs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ObservationProvider(Protocol):
    def validate(self, target: dict[str, Any], budget: ProviderBudget) -> CapabilityState: ...
    def observe(
        self, tenant_id: str, environment: str, target: dict[str, Any], budget: ProviderBudget
    ) -> ProviderResult: ...
