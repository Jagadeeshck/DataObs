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
from .connection import OracleConnectionFactory
from .evidence import safe_evidence
from .normalisation import canonical_type
from .sql import REGISTRY


class OracleDatabaseProvider:
    provider_type = "oracle"
    provider_version = "1"

    def __init__(self, connection_factory=None):
        self._factory = connection_factory or OracleConnectionFactory()
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
            ("CREATE SESSION; accessible ALL_* metadata; explicit SELECT for aggregate targets",),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            (DRIVER_REQUIREMENT,),
            (
                "Oracle AI Database 26ai primary; Oracle Database 19c secondary; features detected from dictionary shape",
            ),
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except ValueError:
            return ValidationResult(
                False, (ValidationIssue("invalid_configuration", "provider", "Oracle configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_configuration(configuration)
            with self._factory.connect(cfg) as connection:
                rows, _ = BoundedStatementExecutor(REGISTRY, 1).execute(connection, "identity")
                validate_product(str(rows[0]["PRODUCT_VERSION"]))
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            code = next(
                (
                    x
                    for x in (
                        "dependency_unavailable",
                        "authentication_failed",
                        "tls_validation_failed",
                        "service_not_found",
                        "unsupported_server_version",
                    )
                    if x in str(exc)
                ),
                "database_unavailable",
            )
            return ConnectionTestResult(False, error_code=code, message="Oracle connection test failed")

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
        instance = hashlib.sha256(f"{cfg.host.lower()}:{cfg.port}/{cfg.service_name.lower()}".encode()).hexdigest()
        identity = DatabaseIdentity(
            context.tenant_id, environment, "oracle", context.integration_id, instance, cfg.service_name
        )
        with self._factory.connect(cfg) as connection:
            executor = BoundedStatementExecutor(REGISTRY, max(cfg.limits.values()))
            health, _ = executor.execute(connection, "identity")
            row = {str(k).lower(): v for k, v in health[0].items()}
            validate_product(str(row["product_version"]))
            try:
                driver_version = importlib.metadata.version("oracledb")
            except importlib.metadata.PackageNotFoundError:
                driver_version = "test-double"
            yield ResourceObservation(
                "oracle",
                identity.canonical_id(),
                environment,
                "database",
                "identity",
                identity.canonical_id(),
                cfg.service_name,
                datetime.now(timezone.utc),
                context.collection_run_id,
                source_evidence={
                    "engine": "oracle",
                    "database_name": row.get("database_name"),
                    "service_name": row.get("service_name"),
                    "container_name": row.get("container_name"),
                    "server_version": row["product_version"],
                    "driver_name": "python-oracledb",
                    "driver_version": driver_version,
                    "driver_mode": "thin",
                    "provider_version": "1",
                    "reachable": True,
                    "raw_rows_persisted": False,
                    "visibility_scope": "collector_principal",
                },
            )
            families = [
                ("schemas", "maximum_schemas"),
                ("tables", "maximum_relations"),
                ("views", "maximum_relations"),
                ("materialized_views", "maximum_relations"),
                (
                    "vector_columns" if cfg.discovery.get("include_vector_metadata", True) else "columns",
                    "maximum_columns",
                ),
                ("constraints", "maximum_constraints"),
                ("indexes", "maximum_indexes"),
                ("partitions", "maximum_partitions"),
            ]
            for statement, limit_name in families:
                family = (
                    "columns"
                    if statement == "vector_columns"
                    else ("relations" if statement in {"tables", "views", "materialized_views"} else statement)
                )
                flag = {
                    "views": "include_views",
                    "materialized_views": "include_materialized_views",
                    "constraints": "include_constraints",
                    "indexes": "include_indexes",
                    "partitions": "include_partitions",
                }.get(statement)
                if flag and cfg.discovery.get(flag, True) is False:
                    continue
                try:
                    try:
                        rows, truncated = executor.execute(connection, statement)
                    except Exception:
                        if statement == "vector_columns":
                            rows, truncated = executor.execute(connection, "columns")
                        else:
                            raise
                    for original in rows[: cfg.limits[limit_name]]:
                        data = {str(k).lower(): v for k, v in original.items()}
                        schema = str(data.get("schema", ""))
                        relation = str(data.get("table", ""))
                        if (
                            cfg.discovery.get("include_schemas") and schema not in cfg.discovery["include_schemas"]
                        ) or schema in cfg.discovery.get("exclude_schemas", ("SYS", "SYSTEM")):
                            continue
                        if relation and (
                            (cfg.discovery.get("include_tables") and relation not in cfg.discovery["include_tables"])
                            or relation in cfg.discovery.get("exclude_tables", ())
                        ):
                            continue
                        safe = safe_evidence(data)
                        if family == "columns":
                            safe["canonical_type"] = canonical_type(str(data.get("native_type", "")))
                        yield ResourceObservation(
                            "oracle",
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
                    yield PartialFailure(
                        "metadata_collection", "metadata_unavailable", f"{family}: collection unavailable", True
                    )
