from datetime import datetime, timedelta, timezone

from ..normalisation import duration_ms, observation, resource_id, value
from ..pagination import bounded


def collect(client, context, cfg, item):
    runs = item["runs"]
    if not runs["enabled"]:
        return
    now = datetime.now(timezone.utc)
    after = now - timedelta(seconds=runs["lookback_seconds"] + runs["overlap_seconds"])
    rg, name = item["resource_group"], item["factory_name"]
    fid = resource_id(cfg, rg, "microsoft.datafactory", "factories", name)
    query = {
        "last_updated_after": after,
        "last_updated_before": now,
        "order_by": [{"order_by": "LastUpdated", "order": "DESC"}],
    }
    for r in bounded(
        client.invoke("adf_pipeline_runs_query", rg, name, query),
        cfg.limits["maximum_pages"],
        runs["maximum_pipeline_runs"],
        lambda x: value(x, "run_id"),
        context,
    ):
        run = value(r, "run_id")
        start, end = value(r, "run_start"), value(r, "run_end")
        yield observation(
            context,
            cfg,
            "global",
            "data_factory",
            "adf.pipeline_run",
            fid + "/runs/" + run,
            run,
            {
                "run_id": run,
                "pipeline_canonical_id": fid + "/pipelines/" + str(value(r, "pipeline_name")),
                "pipeline_name": value(r, "pipeline_name"),
                "run_group_id": value(r, "run_group_id"),
                "is_latest": value(r, "is_latest"),
                "status": value(r, "status"),
                "run_start": start,
                "run_end": end,
                "duration_ms": duration_ms(start, end),
                "last_updated": value(r, "last_updated"),
                "trigger_type": (
                    value(r, "run_dimensions", {}).get("TriggerType")
                    if isinstance(value(r, "run_dimensions", {}), dict)
                    else None
                ),
                "invoked_by_type": value(value(r, "invoked_by", {}), "invoked_by_type"),
            },
        )
        if runs["include_activity_runs"]:
            aq = {"last_updated_after": after, "last_updated_before": now}
            for a in bounded(
                client.invoke("adf_activity_runs_query", rg, name, run, aq),
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
                    "data_factory",
                    "adf.activity_run",
                    fid + "/activity-runs/" + aid,
                    aid,
                    {
                        "pipeline_run_id": run,
                        "activity_run_id": aid,
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
