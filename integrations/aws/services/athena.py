from .common import observation, pages


def collect(client, context, cfg, account, region):
    for summary in pages(client, "list_work_groups", "WorkGroups", token="NextToken", output_token="NextToken"):
        detail = client.get_work_group(WorkGroup=summary["Name"])["WorkGroup"]
        configuration = detail.get("Configuration", {})
        safe = {
            "state": detail.get("State"),
            "engine_version": detail.get("EngineVersion", {}).get("SelectedEngineVersion"),
            "enforce_workgroup_configuration": configuration.get("EnforceWorkGroupConfiguration"),
            "output_encrypted": bool(configuration.get("ResultConfiguration", {}).get("EncryptionConfiguration")),
        }
        yield observation(context, cfg, account, region, "athena", "workgroup", detail["Name"], detail["Name"], safe)
    seen = set()
    for query_id in pages(
        client, "list_query_executions", "QueryExecutionIds", token="NextToken", output_token="NextToken", MaxResults=50
    ):
        if query_id in seen:
            continue
        seen.add(query_id)
        query = client.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        status, stats = query.get("Status", {}), query.get("Statistics", {})
        safe = {
            "status": status.get("State"),
            "submission_at": status.get("SubmissionDateTime"),
            "completion_at": status.get("CompletionDateTime"),
            "duration_ms": stats.get("EngineExecutionTimeInMillis"),
            "bytes_scanned": stats.get("DataScannedInBytes"),
            "data_manifest_present": bool(stats.get("DataManifestLocation")),
            "result_reused": stats.get("ResultReuseInformation", {}).get("ReusedPreviousResult", False),
            "failure_category": "query_failure" if status.get("State") == "FAILED" else None,
        }
        yield observation(context, cfg, account, region, "athena", "query_execution", query_id, query_id, safe)
