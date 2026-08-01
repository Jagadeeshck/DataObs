"""Tenant-safe persistence boundary used by provider executions."""

from __future__ import annotations

from dataclasses import asdict
from typing import Protocol, Sequence

from packages.collectors.sdk import CollectionRunResult, IntegrationConfiguration, IntegrationContext


class ObservationRepository(Protocol):
    async def persist(self, context: IntegrationContext, observations: Sequence[object]) -> None: ...


class RunRepository(Protocol):
    async def persist(
        self,
        context: IntegrationContext,
        configuration: IntegrationConfiguration,
        provider_version: str,
        result: CollectionRunResult,
    ) -> None: ...


class InMemoryObservationRepository:
    """Explicit test repository; production composition must use Elasticsearch."""

    def __init__(self) -> None:
        self.observations: list[tuple[str, object]] = []

    async def persist(self, context, observations):
        self.observations.extend((context.tenant_id, item) for item in observations)


class InMemoryRunRepository:
    def __init__(self) -> None:
        self.runs: list[dict] = []

    async def persist(self, context, configuration, provider_version, result):
        self.runs.append(asdict(result))
