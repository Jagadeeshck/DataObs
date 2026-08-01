from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

from packages.collectors.sdk import ResourceObservation


def account_scope(account: str) -> str:
    return hashlib.sha256(account.upper().encode()).hexdigest()[:24]


def resource(
    row: Mapping[str, Any],
    *,
    context: Any,
    account: str,
    family: str,
    native_id: str,
    name: str,
    evidence: Mapping[str, Any] | None = None,
) -> ResourceObservation:
    return ResourceObservation(
        "snowflake",
        account_scope(account),
        "global",
        family,
        family,
        native_id,
        name,
        datetime.now(timezone.utc),
        context.collection_run_id,
        source_evidence=evidence or dict(row),
    )


def safe_row(row: Mapping[str, Any]) -> dict[str, Any]:
    forbidden = {
        "query_text",
        "user_name",
        "query_tag",
        "client_application_id",
        "client_ip",
        "session_id",
        "role_name",
        "error_message",
        "column_default",
    }
    return {key: value for key, value in row.items() if key.lower() not in forbidden}
