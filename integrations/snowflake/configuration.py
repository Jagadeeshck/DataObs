from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .credentials import validate_reference
from .errors import safe_error

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,254}$")
ACCOUNT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,126}[.-][A-Za-z0-9][A-Za-z0-9_-]{0,126}$")


@dataclass(frozen=True)
class Authentication:
    type: str
    secret_ref: str | None = None
    passphrase_ref: str | None = None
    identity_provider: str | None = None


@dataclass(frozen=True)
class SnowflakeConfiguration:
    account_identifier: str
    user: str
    role: str
    authentication: Authentication
    collector_warehouse: str | None
    include_databases: tuple[str, ...]
    exclude_schemas: tuple[str, ...]
    query_lookback_seconds: int
    query_overlap_seconds: int
    warehouse_lookback_seconds: int
    maximum_query_rows: int
    maximum_databases: int
    maximum_schemas: int
    maximum_objects: int
    maximum_columns: int
    statement_timeout_seconds: int
    network_timeout_seconds: int


def _bounded(data: Mapping[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise safe_error("invalid_configuration")
    return value


def _keys(data: Mapping[str, Any], allowed: set[str]) -> None:
    if set(data) - allowed:
        raise safe_error("invalid_configuration")


def parse_configuration(raw: Mapping[str, Any]) -> SnowflakeConfiguration:
    _keys(
        raw,
        {
            "account_identifier",
            "user",
            "role",
            "authentication",
            "collector_warehouse",
            "include_databases",
            "exclude_schemas",
            "history",
            "catalog",
            "session",
        },
    )
    account, user, role = raw.get("account_identifier"), raw.get("user"), raw.get("role")
    if not isinstance(account, str) or not ACCOUNT.fullmatch(account):
        raise safe_error("invalid_configuration")
    for value in (user, role, raw.get("collector_warehouse", "VALID")):
        if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
            raise safe_error("invalid_configuration")
    assert isinstance(user, str) and isinstance(role, str)
    auth = raw.get("authentication")
    if not isinstance(auth, Mapping):
        raise safe_error("invalid_configuration")
    _keys(auth, {"type", "private_key_ref", "private_key_passphrase_ref", "oauth_token_ref", "identity_provider"})
    kind = auth.get("type")
    if kind not in {"key_pair", "oauth", "workload_identity"}:
        raise safe_error("invalid_configuration")
    ref = (
        auth.get("private_key_ref") if kind == "key_pair" else auth.get("oauth_token_ref") if kind == "oauth" else None
    )
    if kind != "workload_identity":
        validate_reference(ref)
    if auth.get("private_key_passphrase_ref") is not None:
        validate_reference(auth["private_key_passphrase_ref"])
    identity_provider = auth.get("identity_provider")
    if kind == "workload_identity" and identity_provider not in {"AWS", "AZURE", "GCP", "OIDC"}:
        raise safe_error("invalid_configuration")
    inc = tuple(raw.get("include_databases", ()))
    exc = tuple(raw.get("exclude_schemas", ()))
    if (
        len(inc) > 100
        or len(exc) > 100
        or any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in inc + exc)
    ):
        raise safe_error("invalid_configuration")
    history, catalog, session = raw.get("history", {}), raw.get("catalog", {}), raw.get("session", {})
    if not all(isinstance(x, Mapping) for x in (history, catalog, session)):
        raise safe_error("invalid_configuration")
    _keys(
        history, {"query_lookback_seconds", "query_overlap_seconds", "warehouse_lookback_seconds", "maximum_query_rows"}
    )
    _keys(catalog, {"maximum_databases", "maximum_schemas", "maximum_objects", "maximum_columns"})
    _keys(session, {"statement_timeout_seconds", "network_timeout_seconds"})
    lookback = _bounded(history, "query_lookback_seconds", 3600, 60, 604800)
    overlap = _bounded(history, "query_overlap_seconds", 900, 0, lookback)
    return SnowflakeConfiguration(
        account,
        user,
        role,
        Authentication(kind, ref, auth.get("private_key_passphrase_ref"), identity_provider),
        raw.get("collector_warehouse"),
        inc,
        exc,
        lookback,
        overlap,
        _bounded(history, "warehouse_lookback_seconds", 86400, 60, 604800),
        _bounded(history, "maximum_query_rows", 5000, 1, 10000),
        _bounded(catalog, "maximum_databases", 100, 1, 100),
        _bounded(catalog, "maximum_schemas", 2000, 1, 5000),
        _bounded(catalog, "maximum_objects", 50000, 1, 100000),
        _bounded(catalog, "maximum_columns", 200000, 1, 500000),
        _bounded(session, "statement_timeout_seconds", 60, 1, 300),
        _bounded(session, "network_timeout_seconds", 30, 1, 120),
    )
