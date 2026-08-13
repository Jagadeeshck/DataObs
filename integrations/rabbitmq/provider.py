from __future__ import annotations

from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    ConnectionTestResult,
    PartialFailure,
    ProviderCapabilities,
    ValidationIssue,
    ValidationResult,
)

from .client import RabbitMqManagementClient
from .collectors import collect_vhost, collect_vhosts
from .configuration import parse_configuration
from .errors import RabbitMqError
from .evidence import LIMITATIONS, health


class RabbitMqMessagingProvider:
    provider_type = "rabbitmq"
    provider_version = "1"

    def __init__(self, client_factory=None):
        self._client_factory = client_factory or RabbitMqManagementClient
        self._configuration = None

    def capabilities(self):
        supported = frozenset(
            {
                Capability.RESOURCE_DISCOVERY,
                Capability.METADATA_COLLECTION,
                Capability.METRIC_COLLECTION,
                Capability.HEALTH_CHECK,
                Capability.INCREMENTAL_COLLECTION,
            }
        )
        return ProviderCapabilities(
            supported,
            frozenset(set(Capability) - set(supported)),
            ("RabbitMQ monitoring tag", "empty configure/write/read permissions (^$)"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            (),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except RabbitMqError as exc:
            return ValidationResult(
                False, (ValidationIssue(exc.code, exc.endpoint_family, "RabbitMQ configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            client = self._client_factory(parse_configuration(configuration))
            overview = client.overview()
            if str(overview.get("product_name", "RabbitMQ")).lower() != "rabbitmq":
                return ConnectionTestResult(
                    False, error_code="management_api_unavailable", message="Unexpected Management API product"
                )
            client.service_health()
            client.alarm_health()
            return ConnectionTestResult(True, 0)
        except RabbitMqError as exc:
            return ConnectionTestResult(False, error_code=exc.code, message="RabbitMQ connection test failed")

    async def discover(self, context, request):
        async for item in self.collect(
            context, type("Request", (), {"capabilities": frozenset({Capability.RESOURCE_DISCOVERY})})()
        ):
            if not isinstance(item, PartialFailure):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        if self._configuration is None:
            raise RuntimeError("configuration must be validated before collection")
        client = self._client_factory(self._configuration)
        try:
            client.overview()
            client.service_health()
            client.alarm_health()
            yield health(context, True, "management_api_reachable")
        except RabbitMqError as exc:
            yield PartialFailure("health_check", exc.code, "cluster health unavailable", exc.retryable)
        vhosts = []
        try:
            items = list(collect_vhosts(client, context, self._configuration))
            for item in items:
                vhosts.append(item.display_name)
                yield item
        except Exception as exc:
            code = exc.code if isinstance(exc, RabbitMqError) else str(exc)
            yield PartialFailure(
                "resource_discovery",
                code,
                "vhost collection unavailable",
                isinstance(exc, RabbitMqError) and exc.retryable,
            )
        for vhost in vhosts:
            try:
                for item in collect_vhost(client, context, self._configuration, vhost):
                    yield item
            except Exception as exc:
                code = exc.code if isinstance(exc, RabbitMqError) else "partial_collection_failure"
                yield PartialFailure(
                    "metadata_collection",
                    code,
                    "vhost resource collection unavailable",
                    isinstance(exc, RabbitMqError) and exc.retryable,
                )
