from datetime import datetime, timezone

from packages.collectors.sdk import ResourceObservation


def resource(context, cluster, family, native, evidence):
    return ResourceObservation(
        "trino",
        cluster,
        "global",
        "sql_engine",
        family,
        native,
        native,
        datetime.now(timezone.utc),
        context.collection_run_id,
        source_evidence=evidence,
    )
