import hashlib

from .common import observation, pages


def collect(client, context, cfg, account, region):
    definitions = (
        ("get_jobs", "Jobs", "job", "Name"),
        ("get_crawlers", "Crawlers", "crawler", "Name"),
        ("list_workflows", "Workflows", "workflow", None),
        ("list_triggers", "TriggerNames", "trigger", None),
    )
    for method, key, kind, name_key in definitions:
        for raw in pages(client, method, key, token="NextToken", output_token="NextToken"):
            item = raw if isinstance(raw, dict) else {"Name": raw}
            name = item.get(name_key or "Name", str(raw))
            safe = {
                k: item.get(k)
                for k in (
                    "GlueVersion",
                    "WorkerType",
                    "NumberOfWorkers",
                    "MaxCapacity",
                    "Timeout",
                    "ExecutionClass",
                    "State",
                )
                if k in item
            }
            if item.get("Role"):
                safe["role_hash"] = hashlib.sha256(item["Role"].encode()).hexdigest()[:16]
            value = observation(context, cfg, account, region, "glue", kind, name, name, safe)
            if value:
                yield value
            if kind == "job":
                for run in client.get_job_runs(JobName=name, MaxResults=50).get("JobRuns", ()):
                    run_safe = {
                        k: run.get(k)
                        for k in (
                            "JobRunState",
                            "StartedOn",
                            "CompletedOn",
                            "ExecutionTime",
                            "GlueVersion",
                            "WorkerType",
                            "NumberOfWorkers",
                        )
                        if k in run
                    }
                    run_safe["failure_category"] = (
                        "service_failure" if run.get("JobRunState") in {"FAILED", "ERROR", "TIMEOUT"} else None
                    )
                    yield observation(context, cfg, account, region, "glue", "job_run", run["Id"], run["Id"], run_safe)
