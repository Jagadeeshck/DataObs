from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")
_REFS = ("env:", "env://", "file-ref:", "file://", "k8s-file://")


def _closed(value: object, allowed: set[str]):
    if not isinstance(value, Mapping) or set(value) - allowed:
        raise ValueError("invalid_configuration")
    return value


@dataclass(frozen=True)
class OracleConfiguration:
    host: str
    port: int
    service_name: str
    authentication: Mapping[str, str]
    tls: Mapping[str, Any]
    discovery: Mapping[str, Any]
    freshness: Mapping[str, Any]
    profiling: Mapping[str, Any]
    limits: Mapping[str, int]


def parse_configuration(raw: Mapping[str, Any]) -> OracleConfiguration:
    raw = _closed(
        raw, {"host", "port", "service_name", "authentication", "tls", "discovery", "freshness", "profiling", "limits"}
    )
    host = raw.get("host")
    service = raw.get("service_name")
    port = raw.get("port", 1521)
    if not isinstance(host, str) or "://" in host or not _HOST.fullmatch(host):
        raise ValueError("invalid_configuration")
    if not isinstance(service, str) or not _ID.fullmatch(service):
        raise ValueError("invalid_configuration")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("invalid_configuration")
    auth = _closed(raw.get("authentication", {}), {"type", "username", "password_ref"})
    if (
        auth.get("type") != "password"
        or not isinstance(auth.get("username"), str)
        or not _ID.fullmatch(auth["username"])
    ):
        raise ValueError("invalid_configuration")
    ref = auth.get("password_ref")
    if not isinstance(ref, str) or not ref.startswith(_REFS):
        raise ValueError("credential_reference_invalid")
    tls = _closed(
        raw.get("tls", {}),
        {
            "enabled",
            "protocol",
            "verify_server_identity",
            "wallet_location_ref",
            "wallet_password_ref",
            "server_certificate_dn",
        },
    )
    if (
        tls.get("enabled", True) is not True
        or tls.get("protocol", "tcps") != "tcps"
        or tls.get("verify_server_identity", True) is not True
    ):
        raise ValueError("tls_validation_failed")
    for key in ("wallet_location_ref", "wallet_password_ref"):
        value = tls.get(key)
        if value is not None and (not isinstance(value, str) or not value.startswith(_REFS)):
            raise ValueError("credential_reference_invalid")
    discovery = _closed(
        raw.get("discovery", {}),
        {
            "include_schemas",
            "exclude_schemas",
            "include_tables",
            "exclude_tables",
            "include_views",
            "include_materialized_views",
            "include_constraints",
            "include_indexes",
            "include_partitions",
            "include_vector_metadata",
        },
    )
    for key in ("include_schemas", "exclude_schemas", "include_tables", "exclude_tables"):
        values = discovery.get(key, [])
        if not isinstance(values, list) or not all(isinstance(x, str) and _ID.fullmatch(x) for x in values):
            raise ValueError("invalid_configuration")
    for key in (
        "include_views",
        "include_materialized_views",
        "include_constraints",
        "include_indexes",
        "include_partitions",
        "include_vector_metadata",
    ):
        if key in discovery and not isinstance(discovery[key], bool):
            raise ValueError("invalid_configuration")
    freshness = _closed(raw.get("freshness", {}), {"enabled", "relations"})
    profiling = _closed(raw.get("profiling", {}), {"enabled", "relations", "maximum_statements"})
    if not isinstance(freshness.get("enabled", False), bool) or not isinstance(profiling.get("enabled", False), bool):
        raise ValueError("invalid_configuration")
    limits_raw = _closed(
        raw.get("limits", {}),
        {
            "connection_timeout_seconds",
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
        "connection_timeout_seconds": 10,
        "statement_timeout_seconds": 15,
        "maximum_schemas": 1000,
        "maximum_relations": 100000,
        "maximum_columns": 1000000,
        "maximum_constraints": 1000000,
        "maximum_indexes": 500000,
        "maximum_partitions": 500000,
        "maximum_observations": 1000000,
        "total_timeout_seconds": 300,
    }
    limits = {}
    for key, default in defaults.items():
        value = limits_raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("invalid_configuration")
        limits[key] = value
    return OracleConfiguration(
        host,
        port,
        service,
        dict(auth),
        dict(tls),
        dict(discovery),
        dict(freshness) or {"enabled": False},
        dict(profiling) or {"enabled": False},
        limits,
    )
