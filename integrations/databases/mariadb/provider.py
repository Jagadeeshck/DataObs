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
from .connection import MariaDbConnectionFactory
from .evidence import safe_evidence
from .normalisation import canonical_type, storage_engine
from .sql import REGISTRY


class MariaDbDatabaseProvider:
    provider_type = "mariadb"
    provider_version = "1"

    def __init__(self, connection_factory=None):
        self._factory = connection_factory or MariaDbConnectionFactory()
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
            ("catalog visibility; SELECT on explicitly opted-in aggregate targets only",),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            (DRIVER_REQUIREMENT,),
            ("MariaDB 11.8 LTS primary; 11.4 LTS secondary; query history and raw rows unsupported",),
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except ValueError:
            return ValidationResult(
                False, (ValidationIssue("invalid_configuration", "provider", "MariaDB configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_configuration(configuration)
            with self._factory.connect(cfg) as connection:
                rows, _ = BoundedStatementExecutor(REGISTRY, 1).execute(connection, "health")
                validate_product(str(rows[0]["server_version"]), str(rows[0].get("version_comment", "")))
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            if "dependency_unavailable" in str(exc):
                code = "dependency_unavailable"
            elif "server_product_mismatch" in str(exc):
                code = "server_product_mismatch"
            else:
                code = "database_unavailable"
            return ConnectionTestResult(False, error_code=code, message="MariaDB connection test failed")

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
        limits = {
            "schemas": "maximum_schemas",
            "relations": "maximum_relations",
            "columns": "maximum_columns",
            "constraints": "maximum_constraints",
            "indexes": "maximum_indexes",
            "partitions": "maximum_partitions",
        }
        with self._factory.connect(cfg) as connection:
            executor = BoundedStatementExecutor(REGISTRY, max(cfg.limits.values()))
            health, _ = executor.execute(connection, "health")
            validate_product(str(health[0]["server_version"]), str(health[0].get("version_comment", "")))
            try:
                driver_version = importlib.metadata.version("mariadb")
            except importlib.metadata.PackageNotFoundError:
                driver_version = "test-double"
            yield ResourceObservation(
                "mariadb",
                identity.canonical_id(),
                environment,
                "database",
                "identity",
                identity.canonical_id(),
                cfg.database,
                datetime.now(timezone.utc),
                context.collection_run_id,
                source_evidence={
                    "engine": "mariadb",
                    "server_version": str(health[0]["server_version"]),
                    "driver_name": "mariadb",
                    "driver_version": driver_version,
                    "provider_version": self.provider_version,
                    "reachable": True,
                    "raw_rows_persisted": False,
                },
            )
            for family, limit_name in limits.items():
                discovery_flag = {
                    "constraints": "include_constraints",
                    "indexes": "include_indexes",
                    "partitions": "include_partitions",
                }.get(family)
                if discovery_flag and cfg.discovery.get(discovery_flag, True) is False:
                    continue
                try:
                    rows, truncated = executor.execute(connection, family)
                    bound = cfg.limits[limit_name]
                    for row in rows[:bound]:
                        schema, relation = str(row.get("schema", "")), str(row.get("table", ""))
                        if (
                            cfg.discovery.get("include_schemas") and schema not in cfg.discovery["include_schemas"]
                        ) or schema in cfg.discovery.get(
                            "exclude_schemas", ("mariadb", "information_schema", "performance_schema", "sys")
                        ):
                            continue
                        if relation and (
                            (cfg.discovery.get("include_tables") and relation not in cfg.discovery["include_tables"])
                            or relation in cfg.discovery.get("exclude_tables", ())
                        ):
                            continue
                        if row.get("table_type") == "VIEW" and cfg.discovery.get("include_views", True) is False:
                            continue
                        safe = safe_evidence(row)
                        if family == "columns":
                            safe["canonical_type"] = canonical_type(
                                str(row.get("native_type", "")), str(row.get("column_type", ""))
                            )
                        if family == "relations":
                            safe["engine"] = storage_engine(row.get("engine"))
                            safe["row_count_kind"] = "estimated"
                            table_type = str(row.get("table_type", "")).upper()
                            safe["system_versioned"] = "SYSTEM VERSIONED" in table_type
                            safe["resource_category"] = "sequence" if table_type == "SEQUENCE" else "relation"
                        yield ResourceObservation(
                            "mariadb",
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
                    if truncated or len(rows) > bound:
                        yield PartialFailure(
                            "metadata_collection",
                            "result_truncated",
                            f"{family}: configured result bound reached",
                            False,
                        )
                except Exception:
                    yield PartialFailure(
                        "metadata_collection", "metadata_unavailable", f"{family}: collection unavailable", True
                    )
