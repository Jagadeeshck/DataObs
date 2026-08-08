from integrations.sql_engine import BoundedExecutor
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

from .collectors import catalogs, cluster, columns, materialized_views, queries, query_tasks, relations, schemas
from .configuration import parse_configuration
from .connection import TrinoConnectionFactory
from .errors import safe_error
from .evidence import LIMITATIONS, cluster_id
from .sql import REGISTRY


class TrinoSqlEngineProvider:
    provider_type = "trino"
    provider_version = "1"

    def __init__(self, connection_factory=None):
        self._factory, self._configuration = connection_factory or TrinoConnectionFactory(), None

    def capabilities(self):
        return ProviderCapabilities(
            frozenset(
                {
                    Capability.RESOURCE_DISCOVERY,
                    Capability.METADATA_COLLECTION,
                    Capability.METRIC_COLLECTION,
                    Capability.QUERY_HISTORY,
                    Capability.SCHEMA_DISCOVERY,
                    Capability.HEALTH_CHECK,
                    Capability.INCREMENTAL_COLLECTION,
                }
            ),
            frozenset(
                {
                    Capability.LOG_COLLECTION,
                    Capability.LINEAGE_COLLECTION,
                    Capability.COST_COLLECTION,
                    Capability.EVENT_DRIVEN_COLLECTION,
                }
            ),
            ("approved metadata visibility", "system.runtime read when runtime evidence is enabled"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            ("trino>=0.338,<0.339",),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except (ValueError, IntegrationError) as exc:
            return ValidationResult(False, (ValidationIssue(str(exc), "provider", "Trino configuration is invalid"),))

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_configuration(configuration)
            with self._factory.connect(cfg) as connection:
                BoundedExecutor(REGISTRY, fetch_size=1, maximum_rows=1, maximum_pages=1).execute(
                    connection, "validate", deadline_seconds=min(30, context.remaining_seconds)
                )
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            error = safe_error(exc)
            return ConnectionTestResult(False, error_code=str(error.code), message="Trino connection test failed")

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
        cid = cluster_id(cfg.host, cfg.port)
        caps = request.capabilities
        with self._factory.connect(cfg) as connection:
            chosen = []
            if caps & {Capability.RESOURCE_DISCOVERY, Capability.METADATA_COLLECTION, Capability.SCHEMA_DISCOVERY}:
                chosen.append(("catalogs", lambda: catalogs.collect(connection, context, cfg, cid)))
            if (
                caps & {Capability.METRIC_COLLECTION, Capability.HEALTH_CHECK}
                and cfg.runtime["cluster_health"]["enabled"]
            ):
                chosen.append(("cluster_health", lambda: cluster.collect(connection, context, cfg, cid)))
            if Capability.QUERY_HISTORY in caps and cfg.runtime["queries"]["enabled"]:
                chosen.append(("runtime_queries", lambda: queries.collect(connection, context, cfg, cid)))
            if Capability.METRIC_COLLECTION in caps and cfg.runtime["tasks"]["enabled"]:
                chosen.append(("runtime_tasks", lambda: query_tasks.collect(connection, context, cfg, cid)))
            for family, factory in chosen:
                try:
                    items = list(factory())
                    for item in items:
                        yield item
                    if family == "catalogs":
                        for catalog_name in [x.source_evidence["catalog_name"] for x in items]:
                            for subfamily, collector in (
                                ("schemas", schemas.collect),
                                ("relations", relations.collect),
                                ("columns", columns.collect),
                            ):
                                if subfamily == "columns" and not cfg.metadata["include_columns"]:
                                    continue
                                try:
                                    for item in collector(connection, context, cfg, cid, catalog_name):
                                        yield item
                                except Exception as exc:
                                    yield PartialFailure(
                                        "metadata_collection",
                                        str(safe_error(exc).code),
                                        f"{subfamily}: collection unavailable",
                                        True,
                                    )
                        if cfg.metadata["include_materialized_views"]:
                            try:
                                for item in materialized_views.collect(connection, context, cfg, cid):
                                    yield item
                            except Exception as exc:
                                yield PartialFailure(
                                    "metadata_collection",
                                    str(safe_error(exc).code),
                                    "materialized_views: collection unavailable",
                                    True,
                                )
                except Exception as exc:
                    error = safe_error(exc)
                    yield PartialFailure(
                        "metadata_collection", str(error.code), f"{family}: collection unavailable", error.retryable
                    )
