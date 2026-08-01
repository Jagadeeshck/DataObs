"""Bounded orchestration bridge from Collection Manager to SDK providers."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone

from packages.collectors.sdk import (
    CollectionCheckpoint,
    CollectionRequest,
    CollectionRunResult,
    InMemoryCheckpointStore,
    IntegrationConfiguration,
    IntegrationContext,
    PartialFailure,
    ProviderRegistry,
    ResourceObservation,
    RetryPolicy,
    with_retry,
)
from packages.collectors.sdk.errors import CollectionTimeoutError, IntegrationError, InternalCollectorError
from packages.collectors.sdk.redaction import redact_text


class ProviderRuntime:
    """Executes one trusted tenant/integration boundary at a time.

    Providers are instantiated per run, observations are bounded and deduplicated,
    and checkpoints are advanced only after a completed provider iteration.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        checkpoint_store: InMemoryCheckpointStore | None = None,
        *,
        retry_policy: RetryPolicy | None = None,
        maximum_observations: int = 10_000,
    ) -> None:
        if not 1 <= maximum_observations <= 100_000:
            raise ValueError("maximum_observations must be in [1, 100000]")
        self.registry = registry
        self.checkpoints = checkpoint_store or InMemoryCheckpointStore()
        self.retry_policy = retry_policy or RetryPolicy()
        self.maximum_observations = maximum_observations

    async def execute(
        self, context: IntegrationContext, configuration: IntegrationConfiguration
    ) -> CollectionRunResult:
        started = datetime.now(timezone.utc)
        if configuration.integration_id != context.integration_id:
            raise ValueError("trusted context integration_id does not match configuration")
        provider = self.registry.create(configuration.provider_type)
        provider.capabilities().require(configuration.allowed_capabilities)
        validation = await provider.validate_configuration(context, configuration.provider)
        if not validation.valid:
            from packages.collectors.sdk.errors import InvalidConfigurationError

            raise InvalidConfigurationError("provider configuration validation failed")

        capability_key = ",".join(sorted(configuration.allowed_capabilities))
        before = await self.checkpoints.load(context.tenant_id, context.integration_id, capability_key)
        request = CollectionRequest(configuration.allowed_capabilities, checkpoint=before)

        async def collect_once() -> list[object]:
            observations: list[object] = []
            async for observation in provider.collect(context, request):
                if len(observations) >= self.maximum_observations:
                    raise InternalCollectorError("provider observation bound exceeded")
                observations.append(observation)
            return observations

        retries = 0
        failures: list[PartialFailure] = []
        observations: list[object] = []
        try:
            remaining = min(configuration.timeout_seconds, context.remaining_seconds)
            if remaining <= 0:
                raise CollectionTimeoutError("collection deadline elapsed")
            observations, retries = await asyncio.wait_for(
                with_retry(collect_once, self.retry_policy), timeout=remaining
            )
        except asyncio.TimeoutError as exc:
            raise CollectionTimeoutError("collection timed out") from exc
        except asyncio.CancelledError:
            raise
        except IntegrationError as exc:
            if not observations:
                raise
            failures.append(PartialFailure("collection", exc.code, redact_text(exc), exc.retryable))

        # Stable provider identities suppress lookback/pagination overlap in this run.
        unique: dict[str, object] = {}
        skipped = 0
        for position, observation in enumerate(observations):
            if isinstance(observation, PartialFailure):
                failures.append(replace(observation, message=redact_text(observation.message)))
                continue
            identity = getattr(observation, "canonical_id", None) or repr(observation)
            if identity in unique:
                skipped += 1
            else:
                unique[str(identity)] = observation

        after = CollectionCheckpoint(
            context.tenant_id,
            context.integration_id,
            configuration.provider_type,
            capability_key,
            watermark=datetime.now(timezone.utc),
            version=(before.version + 1 if before else 1),
        )
        if configuration.checkpoint_enabled:
            await self.checkpoints.save(after, expected_version=before.version if before else None)
        values = tuple(unique.values())
        return CollectionRunResult(
            context.collection_run_id,
            frozenset(map(str, configuration.allowed_capabilities)),
            frozenset(map(str, configuration.allowed_capabilities)) if not failures else frozenset(),
            started,
            datetime.now(timezone.utc),
            sum(isinstance(item, ResourceObservation) for item in values),
            len(values),
            skipped,
            tuple(failures),
            retries,
            before,
            after if configuration.checkpoint_enabled else before,
            values,  # type: ignore[arg-type]
        )
