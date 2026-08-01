from __future__ import annotations

from typing import Any, AsyncIterator, Mapping, Protocol, runtime_checkable

from .capabilities import ProviderCapabilities
from .context import IntegrationContext
from .discovery import CollectionRequest, DiscoveryRequest
from .observations import ProviderObservation, ResourceObservation
from .validation import ConnectionTestResult, ValidationResult


@runtime_checkable
class IntegrationProvider(Protocol):
    provider_type: str
    provider_version: str

    def capabilities(self) -> ProviderCapabilities: ...

    async def validate_configuration(
        self, context: IntegrationContext, configuration: Mapping[str, Any]
    ) -> ValidationResult: ...

    async def test_connection(
        self, context: IntegrationContext, configuration: Mapping[str, Any]
    ) -> ConnectionTestResult: ...

    def discover(
        self, context: IntegrationContext, request: DiscoveryRequest
    ) -> AsyncIterator[ResourceObservation]: ...

    def collect(
        self, context: IntegrationContext, request: CollectionRequest
    ) -> AsyncIterator[ProviderObservation]: ...
