from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .common import observation, pages

INVENTORY = (
    ("list_domains", "Domains", "domain", "DomainId", "DomainName", "describe_domain", "DomainId"),
    ("list_user_profiles", "UserProfiles", "user_profile", "UserProfileArn", "UserProfileName", None, None),
    ("list_spaces", "Spaces", "space", "SpaceArn", "SpaceName", None, None),
    ("list_apps", "Apps", "app", "AppArn", "AppName", None, None),
    (
        "list_notebook_instances",
        "NotebookInstances",
        "notebook_instance",
        "NotebookInstanceArn",
        "NotebookInstanceName",
        "describe_notebook_instance",
        "NotebookInstanceName",
    ),
    ("list_pipelines", "PipelineSummaries", "pipeline", "PipelineArn", "PipelineName", None, None),
    ("list_endpoints", "Endpoints", "endpoint", "EndpointArn", "EndpointName", "describe_endpoint", "EndpointName"),
    (
        "list_endpoint_configs",
        "EndpointConfigs",
        "endpoint_configuration",
        "EndpointConfigArn",
        "EndpointConfigName",
        None,
        None,
    ),
    (
        "list_model_package_groups",
        "ModelPackageGroupSummaryList",
        "model_package_group",
        "ModelPackageGroupArn",
        "ModelPackageGroupName",
        None,
        None,
    ),
)

SAFE_KEYS = (
    "CreationTime",
    "LastModifiedTime",
    "Status",
    "DomainStatus",
    "AppStatus",
    "NotebookInstanceStatus",
    "EndpointStatus",
    "InstanceType",
    "InstanceCount",
    "VolumeSizeInGB",
    "EnableNetworkIsolation",
)


def _tags(client, arn):
    try:
        return client.list_tags(ResourceArn=arn).get("Tags", ()) if arn else ()
    except Exception:
        return ()


def collect(client, context, cfg, account, region):
    options = (cfg.raw.get("service_options") or {}).get("sagemaker", {})
    for method, key, kind, id_key, name_key, describe, describe_key in INVENTORY:
        if kind == "endpoint" and options.get("include_endpoints") is False:
            continue
        if not hasattr(client, method):
            continue
        for item in pages(client, method, key, token="NextToken", output_token="NextToken", MaxResults=100):
            detail = item
            if describe and hasattr(client, describe):
                detail = getattr(client, describe)(**{describe_key: item.get(name_key) or item.get(id_key)})
            native = detail.get(id_key) or item.get(id_key) or detail.get(name_key) or item.get(name_key)
            name = detail.get(name_key) or item.get(name_key) or native
            safe = {key: detail.get(key) for key in SAFE_KEYS if key in detail}
            yield observation(
                context, cfg, account, region, "sagemaker", kind, native, name, safe, _tags(client, native)
            )

    histories = (
        (
            "include_training_jobs",
            "list_training_jobs",
            "TrainingJobSummaries",
            "training_job",
            "TrainingJobArn",
            "TrainingJobName",
            "TrainingJobStatus",
        ),
        (
            "include_processing_jobs",
            "list_processing_jobs",
            "ProcessingJobSummaries",
            "processing_job",
            "ProcessingJobArn",
            "ProcessingJobName",
            "ProcessingJobStatus",
        ),
        (
            "include_transform_jobs",
            "list_transform_jobs",
            "TransformJobSummaries",
            "transform_job",
            "TransformJobArn",
            "TransformJobName",
            "TransformJobStatus",
        ),
        (
            "include_pipeline_executions",
            "list_pipeline_executions",
            "PipelineExecutionSummaries",
            "pipeline_execution",
            "PipelineExecutionArn",
            "PipelineExecutionDisplayName",
            "PipelineExecutionStatus",
        ),
    )
    lookback = int(options.get("history_lookback_seconds", 86400))
    after = datetime.now(timezone.utc) - timedelta(seconds=lookback)
    limit = int(options.get("maximum_history_items", 200))
    for option, method, key, kind, id_key, name_key, status_key in histories:
        if not options.get(option, True) or not hasattr(client, method):
            continue
        seen = set()
        kwargs = {"MaxResults": min(100, limit)}
        if method != "list_pipeline_executions":
            kwargs["CreationTimeAfter"] = after
        for item in pages(
            client,
            method,
            key,
            token="NextToken",
            output_token="NextToken",
            maximum=max(1, (limit + 99) // 100),
            **kwargs,
        ):
            native = item.get(id_key) or item.get(name_key)
            if not native or native in seen or len(seen) >= limit:
                continue
            seen.add(native)
            status = item.get(status_key)
            safe = {
                "creation_time": item.get("CreationTime") or item.get("StartTime"),
                "last_modified_time": item.get("LastModifiedTime"),
                "end_time": item.get("EndTime"),
                "execution_status": status,
                "failure_category": "job_failure" if status in {"Failed", "Stopped"} else None,
            }
            yield observation(
                context, cfg, account, region, "sagemaker", kind, native, item.get(name_key, native), safe
            )
