from __future__ import annotations

import hashlib
import importlib.metadata
from datetime import datetime, timezone

from integrations.database import BoundedStatementExecutor, DatabaseIdentity
from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    ConnectionTestResult,
    PartialFailure,
    ProviderCapabilities,
    ResourceObservation,
    ValidationIssue,
    ValidationResult,
)

from .compatibility import DRIVER_REQUIREMENT, validate_product
from .configuration import parse_configuration
from .connection import SqlServerConnectionFactory
from .evidence import safe_evidence
from .normalisation import canonical_type
from .sql import REGISTRY


class SqlServerDatabaseProvider:
    provider_type = "sqlserver"
    provider_version = "1"

    def __init__(self, connection_factory=None):
        self._factory = connection_factory or SqlServerConnectionFactory()
        self._configuration = None

    def capabilities(self):
        supported = {
            Capability.RESOURCE_DISCOVERY,
            Capability.METADATA_COLLECTION,
            Capability.SCHEMA_DISCOVERY,
            Capability.METRIC_COLLECTION,
            Capability.HEALTH_CHECK,
            Capability.INCREMENTAL_COLLECTION,
        }
        unsupported = {
            Capability.QUERY_HISTORY,
            Capability.LINEAGE_COLLECTION,
            Capability.LOG_COLLECTION,
            Capability.COST_COLLECTION,
            Capability.EVENT_DRIVEN_COLLECTION,
        }
        return ProviderCapabilities(
            frozenset(supported),
            frozenset(unsupported),
            ("permission-scoped metadata visibility; SELECT on explicitly approved aggregate targets",),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            (DRIVER_REQUIREMENT,),
            ("SQL Server 2025 primary; SQL Server 2022 secondary; Query Store and raw rows unsupported",),
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except ValueError:
            return ValidationResult(
                False, (ValidationIssue("invalid_configuration", "provider", "SQL Server configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_configuration(configuration)
            with self._factory.connect(cfg) as connection:
                rows, _ = BoundedStatementExecutor(REGISTRY, 1).execute(connection, "identity")
                validate_product(str(rows[0]["product_version"]), str(rows[0]["product_name"]))
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            code = next(
                (
                    code
                    for code in ("dependency_unavailable", "server_product_mismatch", "unsupported_server_version")
                    if code in str(exc)
                ),
                "database_unavailable",
            )
            return ConnectionTestResult(False, error_code=code, message="SQL Server connection test failed")

    async def discover(self, context, request):
        async for item in self.collect(context, request):
            if isinstance(item, ResourceObservation):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        if cfg is None:
            raise RuntimeError("configuration must be validated before collection")
        environment = context.attributes.get("environment", "unknown")
        instance = hashlib.sha256(f"{cfg.host.lower()}:{cfg.port}".encode()).hexdigest()
        identity = DatabaseIdentity(
            context.tenant_id, environment, self.provider_type, context.integration_id, instance, cfg.database
        )
        with self._factory.connect(cfg) as connection:
            executor = BoundedStatementExecutor(REGISTRY, max(cfg.limits.values()))
            health, _ = executor.execute(connection, "identity")
            major = validate_product(str(health[0]["product_version"]), str(health[0]["product_name"]))
            try:
                driver_version = importlib.metadata.version("mssql-python")
            except importlib.metadata.PackageNotFoundError:
                driver_version = "test-double"
            yield ResourceObservation(
                "sqlserver",
                identity.canonical_id(),
                environment,
                "database",
                "identity",
                identity.canonical_id(),
                cfg.database,
                datetime.now(timezone.utc),
                context.collection_run_id,
                source_evidence={
                    "engine": "sqlserver",
                    "product_version": str(health[0]["product_version"]),
                    "major_version": major,
                    "edition": health[0].get("edition"),
                    "engine_edition": health[0].get("engine_edition"),
                    "database_name": health[0].get("database_name"),
                    "driver_name": "mssql-python",
                    "driver_version": driver_version,
                    "odbc_binary_package": "mssql-python-odbc",
                    "provider_version": "1",
                    "reachable": True,
                    "raw_rows_persisted": False,
                    "visibility_scope": "collector_principal",
                },
            )
            families = (
                ("schemas", "maximum_schemas"),
                ("relations", "maximum_relations"),
                ("columns_2025" if major >= 17 else "columns_2022", "maximum_columns"),
                ("constraints", "maximum_constraints"),
                ("indexes", "maximum_indexes"),
                ("partitions", "maximum_partitions"),
            )
            if cfg.discovery.get("include_storage_statistics", False):
                families += (("storage_statistics", "maximum_partitions"),)
            for statement, limit_name in families:
                family = "columns" if statement.startswith("columns_") else statement
                flag = {
                    "constraints": "include_constraints",
                    "indexes": "include_indexes",
                    "partitions": "include_partitions",
                }.get(family)
                if flag and cfg.discovery.get(flag, True) is False:
                    continue
                try:
                    rows, truncated = executor.execute(connection, statement)
                    for row in rows[: cfg.limits[limit_name]]:
                        schema, relation = str(row.get("schema", "")), str(row.get("table", ""))
                        if (
                            cfg.discovery.get("include_schemas") and schema not in cfg.discovery["include_schemas"]
                        ) or schema in cfg.discovery.get("exclude_schemas", ("sys", "INFORMATION_SCHEMA")):
                            continue
                        if relation and (
                            (cfg.discovery.get("include_tables") and relation not in cfg.discovery["include_tables"])
                            or relation in cfg.discovery.get("exclude_tables", ())
                        ):
                            continue
                        if row.get("object_type") == "VIEW" and cfg.discovery.get("include_views", True) is False:
                            continue
                        safe = safe_evidence(row)
                        if family == "columns":
                            safe["canonical_type"] = canonical_type(str(row.get("native_type", "")))
                        yield ResourceObservation(
                            "sqlserver",
                            identity.canonical_id(),
                            environment,
                            "database",
                            family.rstrip("s"),
                            identity.canonical_id(schema, relation),
                            f"{schema}.{relation}".strip("."),
                            datetime.now(timezone.utc),
                            context.collection_run_id,
                            source_evidence={
                                **safe,
                                "raw_rows_persisted": False,
                                "visibility_scope": "collector_principal",
                            },
                        )
                    if truncated or len(rows) > cfg.limits[limit_name]:
                        yield PartialFailure(
                            "metadata_collection",
                            "result_truncated",
                            f"{family}: configured result bound reached",
                            False,
                        )
                except Exception:
                    code = (
                        "storage_statistics_unavailable" if family == "storage_statistics" else "metadata_unavailable"
                    )
                    yield PartialFailure("metadata_collection", code, f"{family}: collection unavailable", True)
