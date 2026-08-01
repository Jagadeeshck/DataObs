from __future__ import annotations

import json
from time import monotonic, sleep

from .errors import safe_error
from .normalisation import value
from .system_tables import QUERY_HISTORY_SQL, WAREHOUSE_EVENTS_SQL, validate_templates

TEMPLATES = {"query_history": QUERY_HISTORY_SQL, "warehouse_events": WAREHOUSE_EVENTS_SQL}


def execute_fixed(
    client, family, warehouse_id, parameters, *, timeout_seconds, maximum_rows, maximum_bytes, cancelled=lambda: False
):
    validate_templates()
    if family not in TEMPLATES:
        raise safe_error("unsupported_feature")
    response = client.statement_execution.execute_statement(
        statement=TEMPLATES[family],
        warehouse_id=warehouse_id,
        parameters=[{"name": k, "value": str(v)} for k, v in parameters.items()],
        disposition="INLINE",
        format="JSON_ARRAY",
        wait_timeout="0s",
        byte_limit=maximum_bytes,
    )
    statement_id = value(response, "statement_id")
    deadline = monotonic() + timeout_seconds
    while str(value(value(response, "status", {}), "state", "")).upper() not in {
        "SUCCEEDED",
        "FAILED",
        "CANCELED",
        "CLOSED",
    }:
        if cancelled() or monotonic() >= deadline:
            client.statement_execution.cancel_execution(statement_id=statement_id)
            raise safe_error("statement_cancelled" if cancelled() else "statement_timeout")
        sleep(0.05)
        response = client.statement_execution.get_statement(statement_id=statement_id)
    state = str(value(value(response, "status", {}), "state", "")).upper()
    if state != "SUCCEEDED":
        raise safe_error("statement_failed")
    manifest = value(response, "manifest", {})
    if value(manifest, "truncated", False):
        raise safe_error("result_truncated")
    data = value(value(response, "result", {}), "data_array", ()) or ()
    if len(data) > maximum_rows or len(json.dumps(data)) > maximum_bytes:
        raise safe_error("result_truncated")
    return data
