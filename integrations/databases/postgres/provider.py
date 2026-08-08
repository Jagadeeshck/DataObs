from __future__ import annotations

import hashlib
from contextlib import contextmanager
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

from .configuration import parse_configuration
from .connection import resolve_secret
from .sql import REGISTRY


class PostgreSqlConnectionFactory:
    @contextmanager
    def connect(self, cfg):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("dependency_unavailable") from exc
        ref = cfg.password_ref
        modern_ref = (
            "env://" + ref[4:]
            if ref.startswith("env:")
            else "file://" + ref[9:] if ref.startswith("file-ref:") else ref
        )
        connection = psycopg.connect(
            host=cfg.host,
            port=cfg.port,
            dbname=cfg.database,
            user=cfg.username,
            password=str(resolve_secret(modern_ref)),
            connect_timeout=cfg.limits["connection_timeout_seconds"],
            sslmode=cfg.tls_mode,
            sslrootcert=(
                cfg.ca_bundle_ref[9:] if cfg.ca_bundle_ref and cfg.ca_bundle_ref.startswith("file-ref:") else None
            ),
            application_name="dataobs-collector",
            options=f"-c default_transaction_read_only=on -c statement_timeout={cfg.limits['statement_timeout_seconds'] * 1000}",
            autocommit=True,
        )
        try:
            yield connection
        finally:
            connection.close()


class PostgreSqlDatabaseProvider:
    provider_type = "postgres"
    provider_version = "1"

    def __init__(self, connection_factory=None):
        self._factory, self._configuration = connection_factory or PostgreSqlConnectionFactory(), None

    def capabilities(self):
        return ProviderCapabilities(
            frozenset(
                {
                    Capability.RESOURCE_DISCOVERY,
                    Capability.METADATA_COLLECTION,
                    Capability.SCHEMA_DISCOVERY,
                    Capability.METRIC_COLLECTION,
                    Capability.HEALTH_CHECK,
                    Capability.INCREMENTAL_COLLECTION,
                }
            ),
            frozenset(
                {
                    Capability.QUERY_HISTORY,
                    Capability.LINEAGE_COLLECTION,
                    Capability.EVENT_DRIVEN_COLLECTION,
                    Capability.COST_COLLECTION,
                    Capability.LOG_COLLECTION,
                }
            ),
            ("CONNECT and catalog visibility", "relation SELECT only for explicitly configured freshness/profiling"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            ("psycopg>=3.3,<3.4",),
            (
                "No SQL text, raw rows, defaults, check expressions, index definitions, owners, comments, lineage, or query history",
            ),
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except ValueError:
            return ValidationResult(
                False, (ValidationIssue("invalid_configuration", "provider", "PostgreSQL configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_configuration(configuration)
            with self._factory.connect(cfg) as connection:
                BoundedStatementExecutor(REGISTRY, 1).execute(connection, "health")
            return ConnectionTestResult(True, 0)
        except Exception:
            return ConnectionTestResult(
                False, error_code="database_unavailable", message="PostgreSQL connection test failed"
            )

    async def discover(self, context, request):
        async for item in self.collect(context, request):
            if isinstance(item, ResourceObservation):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        if cfg is None:
            raise RuntimeError("configuration must be validated before collection")
        instance = hashlib.sha256(f"{cfg.host.lower()}:{cfg.port}".encode()).hexdigest()
        environment = context.attributes.get("environment", "unknown")
        identity = DatabaseIdentity(
            context.tenant_id, environment, self.provider_type, context.integration_id, instance, cfg.database
        )
        maximum = max(
            cfg.limits["maximum_relations"],
            cfg.limits["maximum_columns"],
            cfg.limits["maximum_constraints"],
            cfg.limits["maximum_indexes"],
        )
        with self._factory.connect(cfg) as connection:
            executor = BoundedStatementExecutor(REGISTRY, maximum)
            families = (
                ("relations", cfg.limits["maximum_relations"]),
                ("columns", cfg.limits["maximum_columns"]),
                ("constraints", cfg.limits["maximum_constraints"]),
                ("indexes", cfg.limits["maximum_indexes"]),
            )
            for family, bound in families:
                try:
                    rows, truncated = executor.execute(connection, family)
                    for row in rows[:bound]:
                        schema, relation = str(row.get("schema", "")), str(row.get("table", ""))
                        discovery = cfg.discovery
                        if (
                            discovery.get("include_schemas") and schema not in discovery["include_schemas"]
                        ) or schema in discovery.get("exclude_schemas", ()):
                            continue
                        if (
                            discovery.get("include_tables") and relation not in discovery["include_tables"]
                        ) or relation in discovery.get("exclude_tables", ()):
                            continue
                        relation_type = row.get("table_type")
                        if relation_type == "view" and discovery.get("include_views", True) is not True:
                            continue
                        if (
                            relation_type == "materialized_view"
                            and discovery.get("include_materialized_views", True) is not True
                        ):
                            continue
                        safe = {
                            k: v
                            for k, v in row.items()
                            if k
                            not in {
                                "owner",
                                "description",
                                "default",
                                "generation_expression",
                                "check_clause",
                                "index_definition",
                            }
                        }
                        if row.get("constraint_type") == "CHECK":
                            safe["check_constraint_present"] = True
                        yield ResourceObservation(
                            "postgres",
                            identity.canonical_id(),
                            environment,
                            "database",
                            family.rstrip("s"),
                            identity.canonical_id(schema, relation),
                            f"{schema}.{relation}",
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
