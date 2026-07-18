from __future__ import annotations

import socket
from datetime import datetime, timezone
from typing import Any

from packages.agent_sdk.models import (
    ConnectionTestResult,
    ConnectorCapabilities,
    ConnectorCheckpoint,
    DiscoveryResult,
    ErrorCategory,
    FreshnessResult,
    LineageResult,
    ProfileResult,
    QualityResult,
    QueryHistoryResult,
    SchemaSnapshot,
)
from packages.agent_sdk.security import redact

from .connection import connect, query_tag
from .discovery import fetch_catalog
from .freshness import measure_freshness
from .models import PostgresConnectionConfig
from .profiling import profile_table
from .schema import canonicalize_schema, normalise_type, schema_fingerprint


class PostgresConnector:
    def __init__(
        self,
        config: PostgresConnectionConfig | None = None,
        *,
        task_context: dict[str, Any] | None = None,
        scanner_id: str = "local-postgres-scanner",
        secret_provider: Any | None = None,
        connection: Any | None = None,
        dsn: str | None = None,
        allow_schemas=None,
        deny_schemas=None,
        allow_tables=None,
        deny_tables=None,
        statement_timeout_ms: int = 5000,
        application_name: str = "dataobs_scanner",
    ):
        if isinstance(config, str) and dsn is None:
            dsn = config
            config = None
        self.config = config
        self.dsn = dsn
        self.connection = connection
        self._owns_connection = connection is None
        self.task_context = task_context or {}
        self.scanner_id = scanner_id
        self.secret_provider = secret_provider
        self.allow = set(allow_schemas or [])
        self.deny = set(deny_schemas or ["pg_catalog", "information_schema"])
        self.allow_tables = set(allow_tables or [])
        self.deny_tables = set(deny_tables or [])
        self.timeout = config.statement_timeout_ms if config else statement_timeout_ms
        self.application_name = config.application_name if config else application_name
        self._checkpoint: dict[str, Any] = {}

    def __repr__(self):
        target = self.config or self.dsn or "postgres-config"
        return f"PostgresConnector(target={redact(str(target))!r}, statement_timeout_ms={self.timeout})"

    def capabilities(self):
        return ConnectorCapabilities(
            freshness=True, profiling=True, quality=True, lineage=True, query_history=True, emits_raw_rows=False
        )

    def _conn(self):
        if self.connection is None:
            if self.config is None:
                raise ValueError("PostgresConnectionConfig is required outside injected test connections")
            self.connection = connect(self.config)
            self._configure_session()
        return self.connection

    def _configure_session(self) -> None:
        conn = self.connection
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute(
                query_tag(self.scanner_id, self.task_context.get("task_id", "startup"), "configure")
                + "SET default_transaction_read_only = on"
            )
            cur.execute("SET statement_timeout = %s", (self.timeout,))
            cur.execute("SET idle_in_transaction_session_timeout = %s", (self.timeout * 2,))
            cur.execute("SET application_name = %s", (self.application_name,))
        try:
            conn.commit()
        except Exception:
            pass

    def _classify(self, exc: BaseException) -> ErrorCategory:
        msg = str(exc).lower()
        if isinstance(exc, (TimeoutError, socket.timeout)) or "timeout" in msg:
            return ErrorCategory.timeout
        if "auth" in msg or "password" in msg:
            return ErrorCategory.auth
        if "permission" in msg or "privilege" in msg or "denied" in msg:
            return ErrorCategory.permission
        if "ssl" in msg or "tls" in msg or "certificate" in msg:
            return ErrorCategory.network
        if "cancel" in msg:
            return ErrorCategory.timeout
        if "invalid" in msg or "configuration" in msg:
            return ErrorCategory.validation
        if any(s in msg for s in ("could not translate", "connection", "network", "dns", "refused")):
            return ErrorCategory.network
        return ErrorCategory.connector

    def test_connection(self):
        try:
            if (
                self.connection is not None
                and hasattr(self.connection, "execute")
                and not hasattr(self.connection, "cursor")
            ):
                self.connection.execute("SELECT 1")
            else:
                with self._conn().cursor() as cur:
                    cur.execute(
                        query_tag(self.scanner_id, self.task_context.get("task_id", "test"), "test_connection")
                        + "SELECT 1"
                    )
                    cur.fetchone()
            return ConnectionTestResult(True)
        except Exception as e:  # noqa: BLE001
            return ConnectionTestResult(False, str(redact(str(e))), self._classify(e))

    def _filter_schema(self, schema):
        return (not self.allow or schema in self.allow) and schema not in self.deny

    def _filter_table(self, table):
        return (not self.allow_tables or table in self.allow_tables) and table not in self.deny_tables

    def _catalog(self, request=None):
        if self.connection is not None and hasattr(self.connection, "metadata"):
            rows = [
                r
                for r in self.connection.metadata
                if self._filter_schema(r["schema"]) and self._filter_table(r["table"])
            ]
            tables = {(r["database"], r["schema"], r["table"]): r for r in rows}
            return {"tables": list(tables.values()), "columns": rows, "warnings": []}
        task_id = getattr(getattr(request, "metadata", None), "task_id", self.task_context.get("task_id", "task"))
        cat = fetch_catalog(
            self._conn(), self.scanner_id, task_id, self.allow, self.deny, self.allow_tables, self.deny_tables
        )
        cat["warnings"] = cat.get("warnings", [])
        return cat

    def discover(self, request):
        cat = self._catalog(request)
        assets = []
        for row in cat["tables"]:
            assets.append(
                {k: row.get(k) for k in row if k not in {"column", "type", "native_type", "nullable", "default"}}
            )
        request.metadata.ended_at = datetime.now(timezone.utc)
        self._checkpoint["last_discovery"] = request.metadata.ended_at.isoformat()
        return DiscoveryResult(
            request.metadata, sorted(assets, key=lambda a: (a.get("schema", ""), a.get("table", "")))
        )

    def schema_snapshot(self, request):
        cat = self._catalog(request)
        cols = [
            {
                "name": r["column"],
                "type": normalise_type(r.get("type") or r.get("native_type") or ""),
                "native_type": r.get("native_type") or r.get("type"),
                "nullable": bool(r.get("nullable", True)),
                "default": r.get("default"),
                "ordinal_position": r.get("ordinal_position"),
                "identity": r.get("identity"),
                "generated": r.get("generated"),
            }
            for r in cat["columns"]
        ]
        canonical = canonicalize_schema(
            {"columns": cols, "relations": cat["tables"], "warnings": cat.get("warnings", [])}
        )
        fp = schema_fingerprint(canonical)
        request.metadata.ended_at = datetime.now(timezone.utc)
        self._checkpoint["last_schema_fingerprint"] = fp
        return SchemaSnapshot(request.metadata, canonical, fp)

    def profile(self, request):
        if not request.options.get("enable_aggregate_profiling", False):
            return ProfileResult(request.metadata, {"profiling": "disabled"}, raw_rows_persisted=False)
        if self.connection is not None and hasattr(self.connection, "profile"):
            metrics = self.connection.profile(request.options)
        else:
            table = request.options["table"]
            columns = request.options.get("columns", [])
            metrics = profile_table(
                self._conn(), table, columns, enable=True, scanner_id=self.scanner_id, task_id=request.metadata.task_id
            )
        request.metadata.ended_at = datetime.now(timezone.utc)
        self._checkpoint["last_profile"] = request.metadata.ended_at.isoformat()
        return ProfileResult(request.metadata, metrics, raw_rows_persisted=False)

    def freshness(self, request):
        watermarks = measure_freshness(
            self._conn(),
            request.options.get("table"),
            request.options.get("timestamp_column"),
            request.options.get("external_watermark"),
            self.scanner_id,
            request.metadata.task_id,
        )
        request.metadata.ended_at = datetime.now(timezone.utc)
        return FreshnessResult(request.metadata, watermarks)

    def quality(self, request):
        return QualityResult(request.metadata, [{"check": "raw_rows_persisted", "status": "passed", "value": False}])

    def lineage(self, request):
        return LineageResult(request.metadata, request.options.get("openlineage_events", []))

    def query_history(self, request):
        return QueryHistoryResult(request.metadata, [])

    def checkpoint(self):
        tenant_id = self.task_context.get("tenant_id") or self._checkpoint.get("tenant_id")
        integration_id = self.task_context.get("integration_id") or self._checkpoint.get("integration_id")
        if not tenant_id or not integration_id:
            tenant_id = tenant_id or "local-test-tenant"
            integration_id = integration_id or "local-test-integration"
        return ConnectorCheckpoint(
            "postgres", tenant_id, integration_id, {**self._checkpoint, "scanner_id": self.scanner_id}
        )

    def close(self):
        if self.connection is not None:
            try:
                if hasattr(self.connection, "cancel"):
                    pass
                if self._owns_connection and hasattr(self.connection, "close"):
                    self.connection.close()
            finally:
                self.connection = None
