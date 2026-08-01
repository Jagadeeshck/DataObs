from packages.collectors.sdk import EvidenceState, MetricObservation

from ..normalisation import account_scope, resource, safe_row
from ..sql import SQL_TEMPLATES, execute_bounded


def collect(connection, context, cfg, parameters):
    for family in ("warehouse_load", "metering", "storage"):
        for row in execute_bounded(connection, SQL_TEMPLATES[family], parameters, batch_size=100):
            native = str(row.get("warehouse_id") or row.get("table_id"))
            evidence = safe_row(row)
            evidence.update(evidence_freshness="delayed_account_usage", evidence_state="measured")
            if family == "storage":
                evidence["freshness_method"] = "metadata_last_altered"
            yield resource(
                row,
                context=context,
                account=cfg.account_identifier,
                family=family,
                native_id=native + ":" + str(row.get("start_time", "current")),
                name=f"Snowflake {family} evidence",
                evidence=evidence,
            )
            if family == "warehouse_load":
                for name in ("avg_running", "avg_queued_load", "avg_queued_provisioning", "avg_blocked"):
                    value = row.get(name)
                    yield MetricObservation(
                        f"snowflake:{account_scope(cfg.account_identifier)}:{native}",
                        name,
                        float(value) if value is not None else None,
                        EvidenceState.MEASURED if value is not None else EvidenceState.MISSING,
                        "queries",
                        "average",
                        cfg.warehouse_lookback_seconds,
                        row.get("end_time") or parameters["end_time"],
                        "snowflake",
                    )
