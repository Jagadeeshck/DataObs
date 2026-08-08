from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")


def _closed(raw, allowed):
    if not isinstance(raw, Mapping) or set(raw) - set(allowed):
        raise ValueError("invalid_configuration")


def _integer(raw, name, default, maximum):
    value = raw.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError("invalid_configuration")
    return value


@dataclass(frozen=True)
class PostgreSqlConfiguration:
    host: str
    port: int
    database: str
    username: str
    password_ref: str
    tls_mode: str
    ca_bundle_ref: str | None
    discovery: Mapping[str, Any]
    freshness: Mapping[str, Any]
    profiling: Mapping[str, Any]
    limits: Mapping[str, int]


def parse_configuration(raw: Mapping[str, Any]) -> PostgreSqlConfiguration:
    _closed(raw, {"host", "port", "database", "authentication", "tls", "discovery", "freshness", "profiling", "limits"})
    host, database = raw.get("host"), raw.get("database")
    if not isinstance(host, str) or not _HOST.fullmatch(host) or not isinstance(database, str) or not database:
        raise ValueError("invalid_configuration")
    auth = raw.get("authentication", {})
    _closed(auth, {"type", "username", "password_ref"})
    if auth.get("type") != "password" or not isinstance(auth.get("username"), str):
        raise ValueError("invalid_configuration")
    ref = auth.get("password_ref")
    if not isinstance(ref, str) or not ref.startswith(("env:", "file-ref:", "env://", "file://", "k8s-file://")):
        raise ValueError("credential_reference_invalid")
    tls = raw.get("tls", {})
    _closed(tls, {"mode", "ca_bundle_ref"})
    mode = tls.get("mode", "verify-full")
    if mode not in {"verify-full", "verify-ca"}:
        raise ValueError("tls_validation_failed")
    ca = tls.get("ca_bundle_ref")
    if ca is not None and (not isinstance(ca, str) or not ca.startswith(("file-ref:", "env:"))):
        raise ValueError("credential_reference_invalid")
    discovery = raw.get("discovery", {})
    discovery_keys = {
        "include_schemas",
        "exclude_schemas",
        "include_tables",
        "exclude_tables",
        "include_views",
        "include_materialized_views",
        "include_constraints",
        "include_indexes",
        "include_partition_metadata",
    }
    _closed(discovery, discovery_keys)
    for key in ("include_schemas", "exclude_schemas", "include_tables", "exclude_tables"):
        if not isinstance(discovery.get(key, []), list) or not all(isinstance(v, str) for v in discovery.get(key, [])):
            raise ValueError("invalid_configuration")
    freshness, profiling = raw.get("freshness", {}), raw.get("profiling", {})
    _closed(freshness, {"enabled", "relations"})
    _closed(profiling, {"enabled", "allowed_tables", "allowed_columns", "maximum_statements"})
    limits = raw.get("limits", {})
    names = {
        "connection_timeout_seconds",
        "statement_timeout_seconds",
        "maximum_schemas",
        "maximum_relations",
        "maximum_columns",
        "maximum_constraints",
        "maximum_indexes",
        "maximum_partitions",
        "maximum_concurrent_scans",
        "total_timeout_seconds",
    }
    _closed(limits, names)
    defaults = {
        "connection_timeout_seconds": (5, 60),
        "statement_timeout_seconds": (10, 300),
        "maximum_schemas": (1000, 10000),
        "maximum_relations": (100000, 1000000),
        "maximum_columns": (1000000, 5000000),
        "maximum_constraints": (1000000, 5000000),
        "maximum_indexes": (500000, 2000000),
        "maximum_partitions": (100000, 1000000),
        "maximum_concurrent_scans": (4, 32),
        "total_timeout_seconds": (300, 3600),
    }
    bounds = {name: _integer(limits, name, default, maximum) for name, (default, maximum) in defaults.items()}
    port = raw.get("port", 5432)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("invalid_configuration")
    return PostgreSqlConfiguration(
        host,
        port,
        database,
        auth["username"],
        ref,
        mode,
        ca,
        discovery,
        freshness or {"enabled": False},
        profiling or {"enabled": False},
        bounds,
    )
