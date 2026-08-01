from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import monotonic

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

from .collectors import account, catalog, queries, usage, warehouses
from .configuration import parse_configuration
from .connection import SnowflakeConnectionFactory
from .errors import map_connector_error
from .evidence import LIMITATIONS


class SnowflakeWarehouseProvider:
    provider_type = "snowflake"
    provider_version = "1"

    def __init__(self, connection_factory=None):
        self._factory = connection_factory or SnowflakeConnectionFactory()
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
            ("MONITOR USAGE", "IMPORTED PRIVILEGES on SNOWFLAKE", "allowlisted metadata visibility"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            ("snowflake-connector-python>=3.14,<5",),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except IntegrationError as exc:
            return ValidationResult(
                False, (ValidationIssue(str(exc.code), "provider", "Snowflake configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        started = monotonic()
        try:
            cfg = parse_configuration(configuration)
            with self._factory.connect(cfg, "dataobs:connection-test") as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute("SELECT CURRENT_ACCOUNT() AS ACCOUNT_NAME LIMIT %(limit)s", {"limit": 1})
                    cursor.fetchmany(1)
                finally:
                    cursor.close()
            return ConnectionTestResult(True, int((monotonic() - started) * 1000))
        except IntegrationError as exc:
            return ConnectionTestResult(False, error_code=str(exc.code), message="Snowflake connection test failed")
        except Exception as exc:
            safe = map_connector_error(exc)
            return ConnectionTestResult(False, error_code=str(safe.code), message="Snowflake connection test failed")

    async def discover(self, context, request):
        async for item in self.collect(
            context,
            type("Request", (), {"capabilities": frozenset({Capability.RESOURCE_DISCOVERY}), "checkpoint": None})(),
        ):
            if not isinstance(item, PartialFailure):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        if cfg is None:
            raise RuntimeError("configuration must be validated before collection")
        now = datetime.now(timezone.utc)
        watermark = (
            request.checkpoint.watermark
            if request.checkpoint and request.checkpoint.watermark
            else now - timedelta(seconds=cfg.query_lookback_seconds)
        )
        parameters = {
            "start_time": min(
                watermark - timedelta(seconds=cfg.query_overlap_seconds),
                now - timedelta(seconds=cfg.query_lookback_seconds),
            ),
            "end_time": now,
            "watermark": watermark,
            "tie_breaker": "",
            "limit": cfg.maximum_query_rows,
        }
        selected = []
        caps = request.capabilities
        if caps & {Capability.RESOURCE_DISCOVERY, Capability.METADATA_COLLECTION, Capability.SCHEMA_DISCOVERY}:
            selected += [("account", account.collect), ("warehouses", warehouses.collect), ("catalog", catalog.collect)]
        if Capability.QUERY_HISTORY in caps:
            selected.append(("query_history", queries.collect))
        if caps & {Capability.METRIC_COLLECTION, Capability.HEALTH_CHECK}:
            selected.append(("usage", usage.collect))
        with self._factory.connect(cfg, "dataobs:snowflake:v1") as connection:
            for family, collector in selected:
                try:
                    for observation in collector(connection, context, cfg, parameters):
                        if context.remaining_seconds <= 0:
                            raise TimeoutError
                        yield observation
                except Exception as exc:
                    safe = exc if isinstance(exc, IntegrationError) else map_connector_error(exc)
                    yield PartialFailure(
                        "metadata_collection", str(safe.code), f"{family}: collection unavailable", safe.retryable
                    )
