from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    ConnectionTestResult,
    PartialFailure,
    ProviderCapabilities,
    ValidationIssue,
    ValidationResult,
)
from packages.collectors.sdk.errors import IntegrationError

from .clients import AzureClientFactory
from .collectors import adf_runs, adls, data_factory, subscription, synapse, synapse_runs
from .configuration import parse_configuration
from .errors import map_azure_error
from .evidence import LIMITATIONS


class AzureDataPlatformProvider:
    provider_type = "azure"
    provider_version = "1"

    def __init__(self, client_factory=None):
        self._factory = client_factory or AzureClientFactory()
        self._configuration = None

    def capabilities(self):
        return ProviderCapabilities(
            frozenset(
                {
                    Capability.RESOURCE_DISCOVERY,
                    Capability.METADATA_COLLECTION,
                    Capability.METRIC_COLLECTION,
                    Capability.HEALTH_CHECK,
                    Capability.INCREMENTAL_COLLECTION,
                }
            ),
            frozenset(
                {
                    Capability.QUERY_HISTORY,
                    Capability.LOG_COLLECTION,
                    Capability.LINEAGE_COLLECTION,
                    Capability.COST_COLLECTION,
                    Capability.EVENT_DRIVEN_COLLECTION,
                }
            ),
            (
                "narrow Azure management-plane Reader",
                "narrow Storage Blob Data Reader only when ADLS listing is enabled",
            ),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            (
                "azure-identity>=1.19,<2",
                "azure-mgmt-resource>=23,<24",
                "azure-mgmt-datafactory>=9,<10",
                "azure-mgmt-synapse>=2.0,<3",
                "azure-storage-file-datalake>=12.17,<13",
            ),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except (IntegrationError, ValueError) as exc:
            return ValidationResult(
                False,
                (
                    ValidationIssue(
                        str(getattr(exc, "code", "invalid_configuration")), "provider", "Azure configuration is invalid"
                    ),
                ),
            )

    async def test_connection(self, context, configuration):
        client = None
        try:
            cfg = parse_configuration(configuration)
            client = self._factory.create(cfg)
            subscription.validate(client, cfg)
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            safe = exc if isinstance(exc, IntegrationError) else map_azure_error(exc)
            return ConnectionTestResult(False, error_code=str(safe.code), message="Azure connection test failed")
        finally:
            if client:
                self._factory.close(client)

    async def discover(self, context, request):
        async for x in self.collect(context, request):
            if not isinstance(x, PartialFailure):
                yield x

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        if cfg is None:
            raise RuntimeError("configuration must be validated before collection")
        client = self._factory.create(cfg)
        try:
            subscription.validate(client, cfg)
            for resources, collectors in (
                (cfg.data_factories, (data_factory.collect, adf_runs.collect)),
                (cfg.synapse_workspaces, (synapse.collect, synapse_runs.collect)),
                (cfg.adls_gen2, (adls.collect,)),
            ):
                for resource in resources:
                    for collector in collectors:
                        try:
                            for value in collector(client, context, cfg, resource):
                                yield value
                        except Exception as exc:
                            safe = exc if isinstance(exc, IntegrationError) else map_azure_error(exc)
                            yield PartialFailure(
                                "metadata_collection",
                                str(safe.code),
                                f"{collector.__module__.split('.')[-1]}: collection unavailable",
                                safe.retryable,
                            )
        finally:
            self._factory.close(client)
