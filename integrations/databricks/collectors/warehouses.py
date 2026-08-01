from __future__ import annotations

from packages.collectors.sdk import EvidenceState, HealthObservation

from ..normalisation import SAFE_FIELDS, allowlist, observation, value


def collect(client, context, cfg):
    if not cfg.sql_warehouses.get("enabled", True):
        return
    include = set(cfg.sql_warehouses.get("include_ids", ()))
    warehouses = tuple(client.warehouses.list())[: int(cfg.sql_warehouses.get("maximum_warehouses", 500))]
    for item in sorted(warehouses, key=lambda x: str(value(x, "id"))):
        wid = str(value(item, "id"))
        if include and wid not in include:
            continue
        detail = client.warehouses.get(id=wid)
        resource = observation(
            context,
            cfg.expected_workspace_id,
            cfg.cloud,
            "warehouse",
            wid,
            str(value(detail, "name", wid)),
            allowlist(detail, SAFE_FIELDS["warehouse"]),
        )
        yield resource
        state = str(value(detail, "state", "UNKNOWN")).upper()
        status = (
            "degraded"
            if state in {"DEGRADED", "FAILED"}
            else "healthy" if state in {"RUNNING", "STOPPED"} else "unknown"
        )
        yield HealthObservation(
            resource.canonical_id,
            status,
            f"warehouse_state_{state.lower()}",
            EvidenceState.MEASURED,
            "warning" if status == "degraded" else "info",
            resource.observed_at,
            0,
        )
