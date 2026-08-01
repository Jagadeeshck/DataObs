from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

from .authentication import Authentication, parse_authentication
from .errors import safe_error

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,254}$")
WORKSPACE_ID = re.compile(r"^[0-9]{1,32}$")
HOSTS = {
    "aws": re.compile(r"^(?:dbc-[a-z0-9-]+|[a-z0-9-]+)\.(?:cloud\.)?databricks\.com$"),
    "azure": re.compile(r"^adb-[0-9]+\.[0-9]+\.azuredatabricks\.net$"),
    "gcp": re.compile(r"^[a-z0-9-]+\.[0-9]+\.gcp\.databricks\.com$"),
}


def validate_workspace_host(value: object, cloud: str, *, allow_localhost: bool = False) -> str:
    if not isinstance(value, str):
        raise safe_error("invalid_configuration")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port:
        raise safe_error("invalid_configuration")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise safe_error("invalid_configuration")
    host = parsed.hostname.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise safe_error("invalid_configuration")
    if host == "localhost" and allow_localhost:
        return "https://localhost"
    if "accounts." in host or cloud not in HOSTS or not HOSTS[cloud].fullmatch(host):
        raise safe_error("invalid_configuration")
    return f"https://{host}"


@dataclass(frozen=True)
class DatabricksConfiguration:
    cloud: str
    workspace_host: str
    expected_workspace_id: str
    authentication: Authentication
    allow_legacy_pat: bool
    unity_catalog: Mapping[str, Any]
    sql_warehouses: Mapping[str, Any]
    jobs: Mapping[str, Any]
    system_tables: Mapping[str, Any]
    limits: Mapping[str, int]


def _keys(value: Mapping[str, Any], allowed: set[str]) -> None:
    if set(value) - allowed:
        raise safe_error("invalid_configuration")


def _bounded(raw: Mapping[str, Any], name: str, default: int, low: int, high: int) -> int:
    value = raw.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise safe_error("invalid_configuration")
    return value


def parse_configuration(raw: Mapping[str, Any]) -> DatabricksConfiguration:
    _keys(
        raw,
        {
            "cloud",
            "workspace_host",
            "expected_workspace_id",
            "expected_account_id",
            "authentication",
            "allow_legacy_pat",
            "unity_catalog",
            "sql_warehouses",
            "jobs",
            "system_tables",
            "limits",
        },
    )
    cloud = raw.get("cloud")
    workspace_id = raw.get("expected_workspace_id")
    if cloud not in HOSTS or not isinstance(workspace_id, str) or not WORKSPACE_ID.fullmatch(workspace_id):
        raise safe_error("invalid_configuration")
    legacy = raw.get("allow_legacy_pat", False)
    if not isinstance(legacy, bool):
        raise safe_error("invalid_configuration")
    auth = parse_authentication(raw.get("authentication"), allow_legacy_pat=legacy)
    uc, wh, jobs, system, limits = (
        raw.get(k, {}) for k in ("unity_catalog", "sql_warehouses", "jobs", "system_tables", "limits")
    )
    if not all(isinstance(x, Mapping) for x in (uc, wh, jobs, system, limits)):
        raise safe_error("invalid_configuration")
    _keys(
        uc,
        {
            "enabled",
            "include_catalogs",
            "exclude_schemas",
            "include_browse_only",
            "include_columns",
            "include_volumes",
            "maximum_catalogs",
            "maximum_schemas",
            "maximum_tables",
            "maximum_columns",
            "maximum_volumes",
        },
    )
    _keys(wh, {"enabled", "include_ids", "maximum_warehouses"})
    _keys(
        jobs,
        {
            "enabled",
            "include_task_summaries",
            "history_lookback_seconds",
            "history_overlap_seconds",
            "maximum_jobs",
            "maximum_runs",
            "maximum_tasks_per_job",
        },
    )
    _keys(system, {"enabled", "sql_warehouse_id", "query_history", "warehouse_events"})
    _keys(
        limits,
        {
            "maximum_pages",
            "page_size",
            "maximum_observations",
            "statement_timeout_seconds",
            "request_timeout_seconds",
            "maximum_concurrent_requests",
            "maximum_result_bytes",
        },
    )
    include, exclude = tuple(uc.get("include_catalogs", ())), tuple(uc.get("exclude_schemas", ()))
    if any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in include + exclude) or set(include) & set(
        exclude
    ):
        raise safe_error("invalid_configuration")
    validated_limits = {
        "maximum_pages": _bounded(limits, "maximum_pages", 1000, 1, 1000),
        "page_size": _bounded(limits, "page_size", 100, 1, 1000),
        "maximum_observations": _bounded(limits, "maximum_observations", 100000, 1, 100000),
        "statement_timeout_seconds": _bounded(limits, "statement_timeout_seconds", 60, 1, 300),
        "request_timeout_seconds": _bounded(limits, "request_timeout_seconds", 30, 1, 120),
        "maximum_concurrent_requests": _bounded(limits, "maximum_concurrent_requests", 8, 1, 32),
        "maximum_result_bytes": _bounded(limits, "maximum_result_bytes", 1048576, 1024, 10485760),
    }
    if system.get("enabled", False) and (not system.get("sql_warehouse_id") or not workspace_id):
        raise safe_error("invalid_configuration")
    return DatabricksConfiguration(
        cloud,
        validate_workspace_host(raw.get("workspace_host"), cloud),
        workspace_id,
        auth,
        legacy,
        uc,
        wh,
        jobs,
        system,
        validated_limits,
    )
