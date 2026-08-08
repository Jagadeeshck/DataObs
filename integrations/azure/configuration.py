from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from .authentication import Authentication, parse_authentication
from .errors import safe_error
from .identifiers import filesystem, path_prefix, resource_group, service_name, storage_account


@dataclass(frozen=True)
class AzureConfiguration:
    cloud: str
    tenant_id: str
    subscription_id: str
    authentication: Authentication
    data_factories: tuple
    synapse_workspaces: tuple
    adls_gen2: tuple
    limits: Mapping[str, int]


def _keys(x, allowed):
    if not isinstance(x, Mapping) or set(x) - set(allowed):
        raise safe_error("invalid_configuration")


def _int(x, n, d, lo, hi):
    v = x.get(n, d)
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise safe_error("invalid_configuration")
    return v


def _uuid(v):
    try:
        return str(UUID(v))
    except (ValueError, TypeError, AttributeError):
        raise safe_error("invalid_configuration") from None


def _runs(raw):
    raw = raw or {}
    _keys(
        raw,
        {
            "enabled",
            "lookback_seconds",
            "overlap_seconds",
            "maximum_pipeline_runs",
            "include_activity_runs",
            "maximum_activity_runs",
        },
    )
    look = _int(raw, "lookback_seconds", 86400, 60, 2592000)
    overlap = _int(raw, "overlap_seconds", 900, 0, look)
    return {
        "enabled": raw.get("enabled", True),
        "lookback_seconds": look,
        "overlap_seconds": overlap,
        "maximum_pipeline_runs": _int(raw, "maximum_pipeline_runs", 10000, 1, 10000),
        "include_activity_runs": raw.get("include_activity_runs", True),
        "maximum_activity_runs": _int(raw, "maximum_activity_runs", 50000, 1, 50000),
    }


def parse_configuration(raw: Mapping[str, Any]):
    _keys(
        raw,
        {
            "cloud",
            "tenant_id",
            "subscription_id",
            "authentication",
            "data_factories",
            "synapse_workspaces",
            "adls_gen2",
            "limits",
        },
    )
    if raw.get("cloud") != "azure_public":
        raise safe_error("invalid_configuration")
    tenant, sub = _uuid(raw.get("tenant_id")), _uuid(raw.get("subscription_id"))
    auth = parse_authentication(raw.get("authentication"), tenant)
    dfs = []
    for x in raw.get("data_factories", []):
        _keys(x, {"resource_group", "factory_name", "include_pipeline_metadata", "include_trigger_metadata", "runs"})
        dfs.append(
            {
                **x,
                "resource_group": resource_group(x.get("resource_group")),
                "factory_name": service_name(x.get("factory_name")),
                "runs": _runs(x.get("runs")),
            }
        )
    syn = []
    for x in raw.get("synapse_workspaces", []):
        _keys(
            x,
            {
                "resource_group",
                "workspace_name",
                "include_sql_pools",
                "include_spark_pools",
                "include_pipeline_metadata",
                "runs",
            },
        )
        syn.append(
            {
                **x,
                "resource_group": resource_group(x.get("resource_group")),
                "workspace_name": service_name(x.get("workspace_name")),
                "runs": _runs(x.get("runs")),
            }
        )
    adls = []
    for x in raw.get("adls_gen2", []):
        _keys(x, {"resource_group", "storage_account", "include_filesystems", "prefix_observations"})
        po = x.get("prefix_observations", {})
        _keys(
            po,
            {"enabled", "maximum_prefixes", "maximum_paths_per_prefix", "maximum_depth", "emit_path_names", "prefixes"},
        )
        if po.get("emit_path_names", False):
            raise safe_error("unsupported_feature")
        depth = _int(po, "maximum_depth", 5, 1, 20)
        prefixes = tuple(
            {"filesystem": filesystem(p["filesystem"]), "path": path_prefix(p["path"], depth)}
            for p in po.get("prefixes", [])
        )
        po = {
            **po,
            "prefixes": prefixes,
            "enabled": po.get("enabled", False),
            "maximum_prefixes": _int(po, "maximum_prefixes", 50, 1, 50),
            "maximum_paths_per_prefix": _int(po, "maximum_paths_per_prefix", 10000, 1, 10000),
            "maximum_depth": depth,
            "emit_path_names": False,
        }
        if len(prefixes) > po["maximum_prefixes"]:
            raise safe_error("invalid_configuration")
        adls.append(
            {
                **x,
                "resource_group": resource_group(x.get("resource_group")),
                "storage_account": storage_account(x.get("storage_account")),
                "prefix_observations": po,
            }
        )
    limits = raw.get("limits", {})
    _keys(
        limits,
        {
            "maximum_factories",
            "maximum_workspaces",
            "maximum_storage_accounts",
            "maximum_pages",
            "maximum_observations",
            "maximum_concurrent_requests",
            "request_timeout_seconds",
        },
    )
    bounds = {
        n: _int(limits, n, d, 1, h)
        for n, d, h in (
            ("maximum_factories", 50, 50),
            ("maximum_workspaces", 50, 50),
            ("maximum_storage_accounts", 50, 50),
            ("maximum_pages", 1000, 1000),
            ("maximum_observations", 500000, 500000),
            ("maximum_concurrent_requests", 8, 32),
            ("request_timeout_seconds", 30, 120),
        )
    }
    if (
        len(dfs) > bounds["maximum_factories"]
        or len(syn) > bounds["maximum_workspaces"]
        or len(adls) > bounds["maximum_storage_accounts"]
    ):
        raise safe_error("invalid_configuration")
    identities = (
        [("adf", x["resource_group"], x["factory_name"]) for x in dfs]
        + [("synapse", x["resource_group"], x["workspace_name"]) for x in syn]
        + [("adls", x["resource_group"], x["storage_account"]) for x in adls]
    )
    if len(identities) != len(set(identities)) or not identities:
        raise safe_error("invalid_configuration")
    return AzureConfiguration("azure_public", tenant, sub, auth, tuple(dfs), tuple(syn), tuple(adls), bounds)
