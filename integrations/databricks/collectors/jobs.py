from __future__ import annotations

from ..normalisation import SAFE_FIELDS, allowlist, fingerprint, observation, value
from ..pagination import Page, collect_pages


def collect(client, context, cfg):
    if not cfg.jobs.get("enabled", True):
        return
    limits = cfg.limits

    def jobs_page(token):
        response = client.jobs.list(limit=limits["page_size"], page_token=token, expand_tasks=False)
        return Page(
            tuple(value(response, "jobs", response if isinstance(response, (list, tuple)) else ()) or ()),
            value(response, "next_page_token"),
        )

    jobs = collect_pages(
        jobs_page,
        key=lambda x: str(value(x, "job_id")),
        maximum_pages=limits["maximum_pages"],
        maximum_results=int(cfg.jobs.get("maximum_jobs", 5000)),
    )
    for item in jobs:
        jid = str(value(item, "job_id"))
        settings = value(item, "settings", {})
        safe = allowlist(item, SAFE_FIELDS["job"])
        safe.update(allowlist(settings, ("name", "format", "max_concurrent_runs", "timeout_seconds")))
        tasks = tuple(value(settings, "tasks", ()) or ())[: int(cfg.jobs.get("maximum_tasks_per_job", 500))]
        safe["task_count"] = len(tasks)
        if cfg.jobs.get("include_task_summaries", True):
            safe["tasks"] = [
                {
                    "task_key_hash": fingerprint(str(value(t, "task_key"))),
                    "task_type": next(
                        (
                            k
                            for k in ("notebook_task", "spark_python_task", "sql_task", "pipeline_task", "run_job_task")
                            if value(t, k) is not None
                        ),
                        "unknown",
                    ),
                    "dependency_count": len(value(t, "depends_on", ()) or ()),
                    "timeout_seconds": value(t, "timeout_seconds"),
                    "retry_limit": value(t, "max_retries"),
                }
                for t in tasks
            ]
        yield observation(
            context, cfg.expected_workspace_id, cfg.cloud, "job", jid, str(value(settings, "name", jid)), safe
        )

    def runs_page(token):
        response = client.jobs.list_runs(limit=limits["page_size"], page_token=token, expand_tasks=False)
        return Page(tuple(value(response, "runs", ()) or ()), value(response, "next_page_token"))

    runs = collect_pages(
        runs_page,
        key=lambda x: str(value(x, "run_id")),
        maximum_pages=limits["maximum_pages"],
        maximum_results=int(cfg.jobs.get("maximum_runs", 10000)),
    )
    for run in runs:
        rid = str(value(run, "run_id"))
        state = value(run, "state", {})
        safe = allowlist(run, SAFE_FIELDS["job_run"])
        safe.update(allowlist(state, ("life_cycle_state", "result_state")))
        yield observation(context, cfg.expected_workspace_id, cfg.cloud, "job_run_source", rid, fingerprint(rid), safe)
