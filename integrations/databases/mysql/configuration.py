from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_$][A-Za-z0-9_$-]{0,63}$")
_SECRET_PREFIXES = ("env:", "file-ref:", "env://", "file://", "k8s-file://")


def _closed(raw: object, allowed: set[str]) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) - allowed:
        raise ValueError("invalid_configuration")
    return raw


def _strings(raw: Mapping[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        value = raw.get(name, [])
        if not isinstance(value, list) or not all(
            isinstance(item, str) and _IDENTIFIER.fullmatch(item) for item in value
        ):
            raise ValueError("invalid_configuration")


@dataclass(frozen=True)
class MySqlConfiguration:
    host: str
    port: int
    database: str
    username: str
    password_ref: str
    ca_bundle_ref: str
    discovery: Mapping[str, Any]
    freshness: Mapping[str, Any]
    profiling: Mapping[str, Any]
    limits: Mapping[str, int]


def parse_configuration(raw: Mapping[str, Any]) -> MySqlConfiguration:
    raw = _closed(
        raw, {"host", "port", "database", "authentication", "tls", "discovery", "freshness", "profiling", "limits"}
    )
    host, database = raw.get("host"), raw.get("database")
    if not isinstance(host, str) or "://" in host or not _HOST.fullmatch(host):
        raise ValueError("invalid_configuration")
    if not isinstance(database, str) or not _IDENTIFIER.fullmatch(database):
        raise ValueError("invalid_configuration")
    port = raw.get("port", 3306)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("invalid_configuration")
    auth = _closed(raw.get("authentication", {}), {"type", "username", "password_ref"})
    if auth.get("type") != "password" or not isinstance(auth.get("username"), str) or not auth["username"]:
        raise ValueError("invalid_configuration")
    password_ref = auth.get("password_ref")
    if not isinstance(password_ref, str) or not password_ref.startswith(_SECRET_PREFIXES):
        raise ValueError("credential_reference_invalid")
    tls = _closed(raw.get("tls", {}), {"enabled", "verify_certificate", "verify_identity", "ca_bundle_ref"})
    if (
        tls.get("enabled") is not True
        or tls.get("verify_certificate") is not True
        or tls.get("verify_identity") is not True
    ):
        raise ValueError("tls_validation_failed")
    ca = tls.get("ca_bundle_ref")
    if not isinstance(ca, str) or not ca.startswith(("file-ref:", "file://", "k8s-file://")):
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
            "include_dynamic_table_statistics",
        },
    )
    _strings(discovery, ("include_schemas", "exclude_schemas", "include_tables", "exclude_tables"))
    for flag in (
        "include_views",
        "include_constraints",
        "include_indexes",
        "include_partitions",
        "include_dynamic_table_statistics",
    ):
        if flag in discovery and not isinstance(discovery[flag], bool):
            raise ValueError("invalid_configuration")
    freshness = _closed(raw.get("freshness", {}), {"enabled", "relations"})
    profiling = _closed(raw.get("profiling", {}), {"enabled", "relations", "maximum_statements"})
    if not isinstance(freshness.get("enabled", False), bool) or not isinstance(profiling.get("enabled", False), bool):
        raise ValueError("invalid_configuration")
    limits_raw = _closed(
        raw.get("limits", {}),
        {
            "connection_timeout_seconds",
            "read_timeout_seconds",
            "write_timeout_seconds",
            "statement_timeout_seconds",
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
        "connection_timeout_seconds": (5, 60),
        "read_timeout_seconds": (30, 300),
        "write_timeout_seconds": (30, 300),
        "statement_timeout_seconds": (15, 300),
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
    return MySqlConfiguration(
        host,
        port,
        database,
        auth["username"],
        password_ref,
        ca,
        discovery,
        freshness or {"enabled": False},
        profiling or {"enabled": False},
        limits,
    )
