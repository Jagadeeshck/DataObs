from datetime import datetime, timedelta, timezone

from ..normalisation import duration_ms, observation, resource_id, value
from ..pagination import bounded


def collect(client, context, cfg, item):
    runs = item["runs"]
    if not runs["enabled"]:
        return
    now = datetime.now(timezone.utc)
    after = now - timedelta(seconds=runs["lookback_seconds"] + runs["overlap_seconds"])
    rg, name = item["resource_group"], item["workspace_name"]
    wid = resource_id(cfg, rg, "microsoft.synapse", "workspaces", name)
    query = {"last_updated_after": after, "last_updated_before": now, "order_by": "LastUpdated DESC"}
    for r in bounded(
        client.invoke("synapse_pipeline_runs_query", rg, name, query),
        cfg.limits["maximum_pages"],
        runs["maximum_pipeline_runs"],
        lambda x: value(x, "run_id"),
        context,
    ):
        rid = value(r, "run_id")
        start, end = value(r, "run_start"), value(r, "run_end")
        yield observation(
            context,
            cfg,
            "global",
            "synapse",
            "synapse.pipeline_run",
            wid + "/runs/" + rid,
            rid,
            {
                "run_id": rid,
                "pipeline_canonical_id": wid + "/pipelines/" + str(value(r, "pipeline_name")),
                "status": value(r, "status"),
                "run_start": start,
                "run_end": end,
                "duration_ms": duration_ms(start, end),
                "last_updated": value(r, "last_updated"),
                "trigger_type": value(r, "trigger_type"),
                "run_group_id": value(r, "run_group_id"),
            },
        )
        if runs["include_activity_runs"]:
            for a in bounded(
                client.invoke(
                    "synapse_activity_runs_query",
                    rg,
                    name,
                    rid,
                    {"last_updated_after": after, "last_updated_before": now},
                ),
                cfg.limits["maximum_pages"],
                runs["maximum_activity_runs"],
                lambda x: value(x, "activity_run_id"),
                context,
            ):
                aid = value(a, "activity_run_id")
                ast, aen = value(a, "activity_run_start"), value(a, "activity_run_end")
                yield observation(
                    context,
                    cfg,
                    "global",
                    "synapse",
                    "synapse.activity_run",
                    wid + "/activity-runs/" + aid,
                    aid,
                    {
                        "activity_run_id": aid,
                        "pipeline_run_id": rid,
                        "activity_name": value(a, "activity_name"),
                        "activity_type": value(a, "activity_type"),
                        "status": value(a, "status"),
                        "activity_start": ast,
                        "activity_end": aen,
                        "duration_ms": duration_ms(ast, aen),
                        "retry_attempt": value(a, "retry_attempt"),
                        "failure_category": "provider_failure" if value(a, "status") == "Failed" else None,
                    },
                )
