from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$-]{0,127}$")
_SECRET_PREFIXES = ("env:", "file-ref:", "env://", "file://", "k8s-file://")


def _closed(raw: object, allowed: set[str]) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) - allowed:
        raise ValueError("invalid_configuration")
    return raw


@dataclass(frozen=True)
class SqlServerConfiguration:
    host: str
    port: int
    database: str
    authentication: Mapping[str, str]
    tls: Mapping[str, Any]
    discovery: Mapping[str, Any]
    freshness: Mapping[str, Any]
    profiling: Mapping[str, Any]
    limits: Mapping[str, int]


def parse_configuration(raw: Mapping[str, Any]) -> SqlServerConfiguration:
    raw = _closed(
        raw, {"host", "port", "database", "authentication", "tls", "discovery", "freshness", "profiling", "limits"}
    )
    host, database = raw.get("host"), raw.get("database")
    if not isinstance(host, str) or "://" in host or not _HOST.fullmatch(host):
        raise ValueError("invalid_configuration")
    if not isinstance(database, str) or not _IDENTIFIER.fullmatch(database):
        raise ValueError("invalid_configuration")
    port = raw.get("port", 1433)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("invalid_configuration")
    auth = _closed(
        raw.get("authentication", {}), {"type", "username", "password_ref", "client_id", "client_secret_ref"}
    )
    kind = auth.get("type")
    required: tuple[Any, ...]
    refs: tuple[Any, ...]
    if kind == "sql_password":
        required = (auth.get("username"), auth.get("password_ref"))
        refs = (auth.get("password_ref"),)
    elif kind == "entra_managed_identity":
        required, refs = (), ()
    elif kind == "entra_service_principal":
        required = (auth.get("client_id"), auth.get("client_secret_ref"))
        refs = (auth.get("client_secret_ref"),)
    else:
        raise ValueError("invalid_configuration")
    if any(not isinstance(value, str) or not value for value in required):
        raise ValueError("invalid_configuration")
    if any(not isinstance(ref, str) or not ref.startswith(_SECRET_PREFIXES) for ref in refs):
        raise ValueError("credential_reference_invalid")
    tls = _closed(raw.get("tls", {}), {"mode", "trust_server_certificate", "hostname_in_certificate"})
    if (
        tls.get("mode", "strict") not in {"strict", "mandatory"}
        or tls.get("trust_server_certificate", False) is not False
    ):
        raise ValueError("tls_validation_failed")
    hostname = tls.get("hostname_in_certificate")
    if hostname is not None and (not isinstance(hostname, str) or not _HOST.fullmatch(hostname)):
        raise ValueError("tls_validation_failed")
    discovery = _closed(
        raw.get("discovery", {}),
        {
            "include_schemas",
            "exclude_schemas",
            "include_tables",
            "exclude_tables",
            "include_views",
            "include_constraints",
            "include_indexes",
            "include_partitions",
            "include_table_features",
            "include_storage_statistics",
        },
    )
    for name in ("include_schemas", "exclude_schemas", "include_tables", "exclude_tables"):
        values = discovery.get(name, [])
        if not isinstance(values, list) or not all(isinstance(v, str) and _IDENTIFIER.fullmatch(v) for v in values):
            raise ValueError("invalid_configuration")
    for name in (
        "include_views",
        "include_constraints",
        "include_indexes",
        "include_partitions",
        "include_table_features",
        "include_storage_statistics",
    ):
        if name in discovery and not isinstance(discovery[name], bool):
            raise ValueError("invalid_configuration")
    freshness = _closed(raw.get("freshness", {}), {"enabled", "relations"})
    profiling = _closed(raw.get("profiling", {}), {"enabled", "relations", "maximum_statements"})
    if not isinstance(freshness.get("enabled", False), bool) or not isinstance(profiling.get("enabled", False), bool):
        raise ValueError("invalid_configuration")
    limits_raw = _closed(
        raw.get("limits", {}),
        {
            "connection_timeout_seconds",
            "query_timeout_seconds",
            "maximum_schemas",
            "maximum_relations",
            "maximum_columns",
            "maximum_constraints",
            "maximum_indexes",
            "maximum_partitions",
            "maximum_observations",
            "total_timeout_seconds",
        },
    )
    defaults = {
        "connection_timeout_seconds": (10, 60),
        "query_timeout_seconds": (15, 300),
        "maximum_schemas": (1000, 10000),
        "maximum_relations": (100000, 1000000),
        "maximum_columns": (1000000, 5000000),
        "maximum_constraints": (1000000, 5000000),
        "maximum_indexes": (500000, 2000000),
        "maximum_partitions": (500000, 2000000),
        "maximum_observations": (1000000, 5000000),
        "total_timeout_seconds": (300, 3600),
    }
    limits = {}
    for name, (default, maximum) in defaults.items():
        value = limits_raw.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError("invalid_configuration")
        limits[name] = value
    return SqlServerConfiguration(
        host,
        port,
        database,
        dict(auth),
        dict(tls),
        dict(discovery),
        dict(freshness) or {"enabled": False},
        dict(profiling) or {"enabled": False},
        limits,
    )
