from __future__ import annotations

from datetime import datetime, timedelta, timezone

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

from .client import DatabricksClientFactory
from .collectors import jobs, query_history, unity_catalog, warehouse_events, warehouses, workspace
from .configuration import parse_configuration
from .errors import map_sdk_error
from .evidence import LIMITATIONS


class DatabricksLakehouseProvider:
    provider_type = "databricks"
    provider_version = "1"

    def __init__(self, client_factory=None):
        self._factory = client_factory or DatabricksClientFactory()
        self._configuration = None

    def capabilities(self):
        supported = frozenset(
            {
                Capability.RESOURCE_DISCOVERY,
                Capability.METADATA_COLLECTION,
                Capability.METRIC_COLLECTION,
                Capability.QUERY_HISTORY,
                Capability.SCHEMA_DISCOVERY,
                Capability.HEALTH_CHECK,
                Capability.INCREMENTAL_COLLECTION,
            }
        )
        unsupported = frozenset(
            {
                Capability.LOG_COLLECTION,
                Capability.LINEAGE_COLLECTION,
                Capability.COST_COLLECTION,
                Capability.EVENT_DRIVEN_COLLECTION,
            }
        )
        return ProviderCapabilities(
            supported,
            unsupported,
            ("OAuth M2M workspace access", "Unity Catalog read metadata", "CAN VIEW selected jobs and warehouses"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            ("databricks-sdk>=0.60,<1",),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except IntegrationError as exc:
            return ValidationResult(
                False, (ValidationIssue(str(exc.code), "provider", "Databricks configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_configuration(configuration)
            client = self._factory.create(cfg)
            try:
                workspace.collect(client, context, cfg, self._factory.sdk_version())
            finally:
                self._factory.close(client)
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            safe = exc if isinstance(exc, IntegrationError) else map_sdk_error(exc)
            return ConnectionTestResult(False, error_code=str(safe.code), message="Databricks connection test failed")

    async def discover(self, context, request):
        async for item in self.collect(context, request):
            if not isinstance(item, PartialFailure):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        if cfg is None:
            raise RuntimeError("configuration must be validated before collection")
        client = self._factory.create(cfg)
        now = datetime.now(timezone.utc)
        parameters = {
            "workspace_id": cfg.expected_workspace_id,
            "start_time": now - timedelta(hours=1),
            "end_time": now,
            "row_limit": 5000,
        }
        selected = [("workspace", lambda: (workspace.collect(client, context, cfg, self._factory.sdk_version()),))]
        caps = request.capabilities
        if caps & {Capability.RESOURCE_DISCOVERY, Capability.METADATA_COLLECTION, Capability.SCHEMA_DISCOVERY}:
            selected += [
                ("unity_catalog", lambda: unity_catalog.collect(client, context, cfg)),
                ("warehouses", lambda: warehouses.collect(client, context, cfg)),
                ("jobs", lambda: jobs.collect(client, context, cfg)),
            ]
        if Capability.QUERY_HISTORY in caps:
            selected.append(("query_history", lambda: query_history.collect(client, context, cfg, parameters)))
        if caps & {Capability.METRIC_COLLECTION, Capability.HEALTH_CHECK}:
            selected.append(("warehouse_events", lambda: warehouse_events.collect(client, context, cfg, parameters)))
        try:
            for family, collector in selected:
                try:
                    for item in collector():
                        if context.remaining_seconds <= 0:
                            raise TimeoutError
                        yield item
                except Exception as exc:
                    safe = exc if isinstance(exc, IntegrationError) else map_sdk_error(exc)
                    yield PartialFailure(
                        "metadata_collection", str(safe.code), f"{family}: collection unavailable", safe.retryable
                    )
        finally:
            self._factory.close(client)
