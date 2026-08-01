"""Bounded dbt invocation/node evidence normalisation."""

import hashlib
from typing import Any


def normalize_dbt_event(value: dict[str, Any]) -> dict[str, Any]:
    invocation = str(value.get("invocation_id") or "")[:512]
    unique_id = str(value.get("unique_id") or "")[:1024]
    if not invocation or not unique_id:
        raise ValueError("dbt invocation_id and unique_id are required")
    code = value.get("compiled_code") or value.get("compiled_sql")
    return {
        "platform": "dbt",
        "invocation_id": invocation,
        "unique_id": unique_id,
        "resource_type": str(value.get("resource_type") or "unknown")[:128],
        "status": str(value.get("status") or "unknown")[:128],
        "compiled_code_fingerprint": hashlib.sha256(str(code).encode()).hexdigest() if code is not None else None,
        "depends_on": [str(x)[:1024] for x in value.get("depends_on", [])[:1000]],
    }
