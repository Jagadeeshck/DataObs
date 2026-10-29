from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from packages.collectors.sdk import (
    Capability,
    InMemoryCheckpointStore,
    IntegrationConfiguration,
    IntegrationContext,
    ProviderCapabilities,
    ProviderRegistry,
    ResourceObservation,
    RetryPolicy,
    ValidationResult,
)
from packages.collectors.sdk.errors import CollectionTimeoutError, MalformedProviderResponseError
from services.collection_manager.provider_runtime import ProviderRuntime
from services.collection_manager.provider_storage import InMemoryObservationRepository, InMemoryRunRepository


def runtime_for(registry, **kwargs):
    return ProviderRuntime(
        registry, InMemoryCheckpointStore(), InMemoryObservationRepository(), InMemoryRunRepository(), **kwargs
    )


class RuntimeProvider:
    provider_type = "runtime_test"
    provider_version = "1.0.0"
    delay = 0.0

    def capabilities(self):
        return ProviderCapabilities(frozenset({Capability.RESOURCE_DISCOVERY}))

    async def validate_configuration(self, context, configuration):
        return ValidationResult(True)

    async def test_connection(self, context, configuration):
        raise NotImplementedError

    async def discover(self, context, request):
        if False:
            yield None

    async def collect(self, context, request):
        await asyncio.sleep(self.delay)
        for native_id in ("a", "a", "b"):
            yield ResourceObservation(
                self.provider_type,
                "account",
                "region",
                "service",
                "type",
                native_id,
                native_id,
                datetime.now(timezone.utc),
                context.collection_run_id,
            )


def inputs(timeout=1):
    context = IntegrationContext(
        "tenant-a", "integration-a", "run-a", datetime.now(timezone.utc) + timedelta(seconds=timeout)
    )
    config = IntegrationConfiguration(
        "v1",
        "integration-a",
        "runtime_test",
        True,
        timeout,
        frozenset({Capability.RESOURCE_DISCOVERY}),
        provider={},
    )
    return context, config


def test_runtime_deduplicates_and_advances_tenant_checkpoint():
    async def scenario():
        registry = ProviderRegistry()
        registry.register(RuntimeProvider)
        runtime = runtime_for(registry, retry_policy=RetryPolicy(1, 1, 0, 0, 0))
        context, config = inputs()
        first = await runtime.execute(context, config)
        second = await runtime.execute(context, config)
        assert (first.emitted_observations, first.skipped, first.discovered_resources) == (2, 1, 2)
        assert first.checkpoint_before is None and first.checkpoint_after.version == 1
        assert second.checkpoint_before.version == 1 and second.checkpoint_after.version == 2
        assert second.checkpoint_after.tenant_id == "tenant-a"

    asyncio.run(scenario())


def test_runtime_rejects_context_configuration_identity_mismatch():
    async def scenario():
        registry = ProviderRegistry()
        registry.register(RuntimeProvider)
        runtime = runtime_for(registry)
        context, config = inputs()
        other = IntegrationConfiguration(
            "v1", "integration-b", config.provider_type, True, 1, config.allowed_capabilities
        )
        with pytest.raises(ValueError, match="trusted context"):
            await runtime.execute(context, other)

    asyncio.run(scenario())


def test_runtime_enforces_timeout_and_propagates_cancellation():
    async def scenario():
        RuntimeProvider.delay = 0.1
        registry = ProviderRegistry()
        registry.register(RuntimeProvider)
        runtime = runtime_for(registry)
        context, config = inputs(0.01)
        with pytest.raises(CollectionTimeoutError):
            await runtime.execute(context, config)
        context, config = inputs(5)
        task = asyncio.create_task(runtime.execute(context, config))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        RuntimeProvider.delay = 0

    asyncio.run(scenario())


class MalformedRuntimeProvider(RuntimeProvider):
    provider_type = "malformed_runtime_test"

    async def collect(self, context, request):
        yield {"unexpected": "mapping"}


class FailingObservationRepository:
    async def persist(self, context, observations):
        raise RuntimeError("synthetic observation persistence failure")


def test_runtime_rejects_malformed_observation_without_persistence_or_checkpoint():
    async def scenario():
        registry = ProviderRegistry()
        registry.register(MalformedRuntimeProvider)
        checkpoints = InMemoryCheckpointStore()
        observations = InMemoryObservationRepository()
        runs = InMemoryRunRepository()
        runtime = ProviderRuntime(registry, checkpoints, observations, runs)
        context = IntegrationContext(
            "tenant-a", "integration-a", "run-malformed", datetime.now(timezone.utc) + timedelta(seconds=5)
        )
        config = IntegrationConfiguration(
            "v1",
            "integration-a",
            "malformed_runtime_test",
            True,
            1,
            frozenset({Capability.RESOURCE_DISCOVERY}),
            provider={},
        )
        with pytest.raises(MalformedProviderResponseError):
            await runtime.execute(context, config)
        assert observations.observations == []
        assert runs.runs == []
        assert await checkpoints.load("tenant-a", "integration-a", "resource_discovery") is None

    asyncio.run(scenario())


def test_runtime_does_not_advance_checkpoint_when_observation_persistence_fails():
    async def scenario():
        registry = ProviderRegistry()
        registry.register(RuntimeProvider)
        checkpoints = InMemoryCheckpointStore()
        runs = InMemoryRunRepository()
        runtime = ProviderRuntime(registry, checkpoints, FailingObservationRepository(), runs)
        context, config = inputs()
        with pytest.raises(RuntimeError, match="observation persistence failure"):
            await runtime.execute(context, config)
        assert runs.runs == []
        assert await checkpoints.load("tenant-a", "integration-a", "resource_discovery") is None

    asyncio.run(scenario())
