from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

import pytest

from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    CollectionRequest,
    CredentialReference,
    CredentialReferenceType,
    DiscoveryRequest,
    EvidenceState,
    IntegrationConfiguration,
    IntegrationContext,
    MetricObservation,
    ProviderCapabilities,
    ProviderRegistry,
    ResourceObservation,
    RetryPolicy,
    ValidationResult,
    canonical_resource_id,
    with_retry,
)
from packages.collectors.sdk.errors import (
    AuthenticationError,
    InvalidConfigurationError,
    TransientProviderError,
    UnsupportedCapabilityError,
)
from packages.collectors.sdk.redaction import redact_mapping, redact_text


class ExampleProvider:
    provider_type = "example_test"
    provider_version = "1.0.0"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            frozenset({Capability.RESOURCE_DISCOVERY, Capability.INCREMENTAL_COLLECTION}),
            frozenset({Capability.METRIC_COLLECTION, Capability.LOG_COLLECTION}),
            required_permissions=("example:list",),
            collection_modes=frozenset({CollectionMode.SCHEDULED}),
            evidence_limitations=("synthetic test evidence only",),
        )

    async def validate_configuration(self, context, configuration):
        return ValidationResult(configuration.get("valid", True))

    async def test_connection(self, context, configuration):
        raise NotImplementedError

    async def discover(self, context, request):
        if False:
            yield None

    async def collect(self, context, request):
        for native_id in ("one", "one", "two"):
            yield ResourceObservation(
                self.provider_type,
                "account",
                "region",
                "service",
                "thing",
                native_id,
                native_id,
                datetime.now(timezone.utc),
                context.collection_run_id,
            )


def context(tenant: str = "tenant-a", integration: str = "integration-a", timeout: float = 5) -> IntegrationContext:
    return IntegrationContext(tenant, integration, "run-1", datetime.now(timezone.utc) + timedelta(seconds=timeout))


def configuration(**provider):
    return IntegrationConfiguration(
        "v1",
        "integration-a",
        "example_test",
        True,
        2,
        frozenset({Capability.RESOURCE_DISCOVERY}),
        provider=provider,
    )


def test_registry_is_explicit_deterministic_and_isolated():
    first = ProviderRegistry()
    second = ProviderRegistry()
    first.register(ExampleProvider)
    assert first.provider_types() == ("example_test",)
    assert second.provider_types() == ()
    assert first.create("example_test").provider_version == "1.0.0"
    with pytest.raises(ValueError, match="already registered"):
        first.register(ExampleProvider)
    with pytest.raises(KeyError, match="unknown provider"):
        first.create("untrusted.module.Provider")


def test_capability_negotiation_rejects_unsupported_operation():
    with pytest.raises(UnsupportedCapabilityError, match="metric_collection"):
        ExampleProvider().capabilities().require(frozenset({Capability.METRIC_COLLECTION}))


def test_configuration_rejects_secret_and_tenant_override():
    with pytest.raises(InvalidConfigurationError, match="trusted or secret"):
        configuration(tenant_id="attacker")
    with pytest.raises(InvalidConfigurationError, match="trusted or secret"):
        configuration(password="cleartext")
    reference = CredentialReference(CredentialReferenceType.ENVIRONMENT, "SECRET_NAME")
    assert "SECRET_NAME" not in repr(reference)


def test_redaction_is_recursive_bounded_and_preserves_safe_values():
    value = redact_mapping({"password": "bad", "nested": {"Authorization": "Bearer bad"}, "count": 0})
    assert value == {"password": "[REDACTED]", "nested": {"Authorization": "[REDACTED]"}, "count": 0}
    assert "abc" not in redact_text("request token=abc")


def test_pagination_and_resource_identity_are_bounded_and_deterministic():
    assert DiscoveryRequest(page_size=1000).page_size == 1000
    with pytest.raises(ValueError, match="page_size"):
        DiscoveryRequest(page_size=1001)
    first = canonical_resource_id("aws", "000000000000", "eu-west-1", "rds", "db-a")
    assert first == canonical_resource_id("aws", "000000000000", "eu-west-1", "rds", "db-a")
    assert first != canonical_resource_id("aws", "000000000000", "eu-west-2", "rds", "db-a")


def test_measured_zero_is_distinct_from_missing():
    timestamp = datetime.now(timezone.utc)
    measured = MetricObservation("r", "connections", 0, EvidenceState.MEASURED, "count", "average", 60, timestamp, "p")
    missing = MetricObservation("r", "connections", None, EvidenceState.MISSING, "count", "average", 60, timestamp, "p")
    assert measured.value == 0 and missing.value is None
    with pytest.raises(ValueError, match="non-measured"):
        MetricObservation("r", "x", 0, EvidenceState.UNKNOWN, "count", "average", 60, timestamp, "p")


def test_retry_is_bounded_and_honours_retryability():
    async def scenario():
        attempts = 0

        async def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise TransientProviderError("temporary")
            return "ok"

        result, retries = await with_retry(flaky, RetryPolicy(3, 1, 0, 0, 0), random_source=random.Random(1))
        assert (result, retries, attempts) == ("ok", 2, 3)

        async def auth_failure():
            raise AuthenticationError("invalid token=not-safe")

        with pytest.raises(AuthenticationError):
            await with_retry(auth_failure, RetryPolicy(3, 1, 0, 0, 0))

    asyncio.run(scenario())


def test_retry_propagates_cancellation():
    async def scenario():
        async def cancelled():
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await with_retry(cancelled, RetryPolicy())

    asyncio.run(scenario())
