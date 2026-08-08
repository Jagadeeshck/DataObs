import re
from dataclasses import dataclass
from typing import Any, Mapping

from .authentication import Authentication, parse_authentication

_HOST = re.compile(
    r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
)


def _keys(raw, allowed):
    if not isinstance(raw, Mapping) or set(raw) - set(allowed):
        raise ValueError("invalid_configuration")


def _integer(raw, name, default, low, high):
    value = raw.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("invalid_configuration")
    return value


@dataclass(frozen=True)
class TrinoConfiguration:
    host: str
    port: int
    authentication: Authentication
    ca_bundle_ref: str | None
    catalog_include: tuple[str, ...]
    catalog_exclude: tuple[str, ...]
    schema_include: tuple[str, ...]
    schema_exclude: tuple[str, ...]
    metadata: Mapping[str, bool]
    runtime: Mapping[str, Mapping[str, Any]]
    limits: Mapping[str, int]


def _filter(raw):
    raw = raw or {}
    _keys(raw, {"include", "exclude"})
    for value in (*raw.get("include", []), *raw.get("exclude", [])):
        if not isinstance(value, str) or not value or len(value) > 255 or any(x in value for x in (";", "--", "\x00")):
            raise ValueError("invalid_configuration")
    return tuple(raw.get("include", [])), tuple(raw.get("exclude", []))


def parse_configuration(raw: Mapping[str, Any]) -> TrinoConfiguration:
    _keys(raw, {"host", "port", "authentication", "tls", "catalogs", "schemas", "metadata", "runtime", "limits"})
    host = raw.get("host")
    if not isinstance(host, str) or not _HOST.fullmatch(host) or any(c in host for c in "/@?#:"):
        raise ValueError("invalid_configuration")
    port = _integer(raw, "port", 8443, 1, 65535)
    tls = raw.get("tls", {"verify": True})
    _keys(tls, {"verify", "ca_bundle_ref"})
    if tls.get("verify", True) is not True:
        raise ValueError("tls_validation_failed")
    ca = tls.get("ca_bundle_ref")
    if ca is not None and (not isinstance(ca, str) or not (ca.startswith("file-ref:") or ca.startswith("env:"))):
        raise ValueError("credential_reference_invalid")
    ci, ce = _filter(raw.get("catalogs"))
    si, se = _filter(raw.get("schemas"))
    metadata = raw.get("metadata", {})
    _keys(metadata, {"include_tables", "include_views", "include_materialized_views", "include_columns"})
    metadata = {
        k: metadata.get(k, True)
        for k in ("include_tables", "include_views", "include_materialized_views", "include_columns")
    }
    runtime = raw.get("runtime", {})
    _keys(runtime, {"cluster_health", "queries", "tasks"})
    health = runtime.get("cluster_health", {})
    _keys(health, {"enabled"})
    queries = runtime.get("queries", {})
    _keys(queries, {"enabled", "lookback_seconds", "overlap_seconds", "maximum_queries"})
    look = _integer(queries, "lookback_seconds", 1800, 60, 86400)
    overlap = _integer(queries, "overlap_seconds", 300, 0, look)
    tasks = runtime.get("tasks", {})
    _keys(tasks, {"enabled", "maximum_queries", "maximum_tasks"})
    runtime_v = {
        "cluster_health": {"enabled": health.get("enabled", True)},
        "queries": {
            "enabled": queries.get("enabled", True),
            "lookback_seconds": look,
            "overlap_seconds": overlap,
            "maximum_queries": _integer(queries, "maximum_queries", 5000, 1, 5000),
        },
        "tasks": {
            "enabled": tasks.get("enabled", True),
            "maximum_queries": _integer(tasks, "maximum_queries", 1000, 1, 1000),
            "maximum_tasks": _integer(tasks, "maximum_tasks", 20000, 1, 20000),
        },
    }
    limits = raw.get("limits", {})
    names = {
        "maximum_catalogs",
        "maximum_schemas_per_catalog",
        "maximum_relations_per_schema",
        "maximum_columns",
        "maximum_pages",
        "fetch_size",
        "maximum_rows_per_statement",
        "maximum_concurrent_catalogs",
        "statement_timeout_seconds",
        "total_timeout_seconds",
        "maximum_observations",
    }
    _keys(limits, names)
    specs = (
        ("maximum_catalogs", 100, 100),
        ("maximum_schemas_per_catalog", 5000, 5000),
        ("maximum_relations_per_schema", 50000, 50000),
        ("maximum_columns", 500000, 500000),
        ("maximum_pages", 1000, 1000),
        ("fetch_size", 500, 5000),
        ("maximum_rows_per_statement", 50000, 50000),
        ("maximum_concurrent_catalogs", 4, 16),
        ("statement_timeout_seconds", 30, 120),
        ("total_timeout_seconds", 300, 3600),
        ("maximum_observations", 500000, 500000),
    )
    bounds = {n: _integer(limits, n, d, 1, h) for n, d, h in specs}
    if bounds["fetch_size"] > bounds["maximum_rows_per_statement"]:
        raise ValueError("invalid_configuration")
    return TrinoConfiguration(
        host, port, parse_authentication(raw.get("authentication", {})), ca, ci, ce, si, se, metadata, runtime_v, bounds
    )
