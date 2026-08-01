from .common import observation, pages


def collect(client, context, cfg, account, region):
    for app in pages(
        client, "list_applications", "applications", token="nextToken", output_token="nextToken", maxResults=50
    ):
        detail = client.get_application(applicationId=app["id"])["application"]
        safe = {
            k: detail.get(k)
            for k in (
                "name",
                "releaseLabel",
                "state",
                "architecture",
                "initialCapacity",
                "maximumCapacity",
                "autoStartConfiguration",
                "autoStopConfiguration",
            )
            if k in detail
        }
        yield observation(
            context,
            cfg,
            account,
            region,
            "emr-serverless",
            "application",
            detail["applicationId"],
            detail.get("name", detail["applicationId"]),
            safe,
            detail.get("tags", {}),
        )
        for run in pages(
            client,
            "list_job_runs",
            "jobRuns",
            token="nextToken",
            output_token="nextToken",
            applicationId=detail["applicationId"],
            maxResults=50,
        ):
            value = client.get_job_run(applicationId=detail["applicationId"], jobRunId=run["id"])["jobRun"]
            run_safe = {
                k: value.get(k)
                for k in ("type", "state", "createdAt", "startedAt", "updatedAt", "totalResourceUtilization")
                if k in value
            }
            run_safe["failure_category"] = "job_failure" if value.get("state") in {"FAILED", "CANCELLED"} else None
            yield observation(
                context,
                cfg,
                account,
                region,
                "emr-serverless",
                "job_run",
                value["jobRunId"],
                value["jobRunId"],
                run_safe,
                value.get("tags", {}),
            )
