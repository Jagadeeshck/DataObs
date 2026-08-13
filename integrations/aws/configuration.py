from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from packages.collectors.sdk.errors import InvalidConfigurationError

SERVICES = frozenset(
    {
        "rds",
        "glue",
        "athena",
        "emr-serverless",
        "s3",
        "lambda",
        "sagemaker",
        "mwaa",
        "redshift",
        "redshift-serverless",
        "kinesis",
        "sqs",
    }
)
REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
ACCOUNT = re.compile(r"^\d{12}$")
ROLE = re.compile(r"^arn:aws(?:-us-gov)?:iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]{1,512}$")
ALLOWED = {
    "expected_account_id",
    "assume_role",
    "regions",
    "services",
    "resource_filters",
    "cloudwatch",
    "ownership_tag_keys",
    "limits",
    "history_overlap_seconds",
    "service_options",
    "sts_endpoint_url",
}


@dataclass(frozen=True)
class AwsConfiguration:
    expected_account_id: str | None
    regions: tuple[str, ...]
    services: tuple[str, ...]
    raw: Mapping[str, Any]


def parse_configuration(raw: Mapping[str, Any]) -> AwsConfiguration:
    unknown = set(raw) - ALLOWED
    if unknown:
        raise InvalidConfigurationError("unknown AWS configuration keys")
    regions = tuple(raw.get("regions") or ())
    services = tuple(raw.get("services") or ())
    if not regions or len(regions) > 20 or any(not REGION.fullmatch(str(x)) for x in regions):
        raise InvalidConfigurationError("one to twenty explicit valid AWS regions are required")
    if not services or len(services) > len(SERVICES) or not set(services) <= SERVICES:
        raise InvalidConfigurationError("unsupported or empty AWS service selection")
    account = raw.get("expected_account_id")
    if account is not None and not ACCOUNT.fullmatch(str(account)):
        raise InvalidConfigurationError("invalid AWS account ID")
    role = raw.get("assume_role") or {}
    if set(role) - {"role_arn", "external_id_ref", "session_duration_seconds"}:
        raise InvalidConfigurationError("unknown assume_role key")
    if role and not ROLE.fullmatch(str(role.get("role_arn", ""))):
        raise InvalidConfigurationError("invalid role ARN")
    duration = int(role.get("session_duration_seconds", 3600))
    if not 900 <= duration <= 43200:
        raise InvalidConfigurationError("role session duration is out of bounds")
    cw = raw.get("cloudwatch") or {}
    if set(cw) - {"enabled", "lookback_seconds", "period_seconds"}:
        raise InvalidConfigurationError("unknown cloudwatch key")
    if not 60 <= int(cw.get("lookback_seconds", 900)) <= 86400:
        raise InvalidConfigurationError("CloudWatch lookback is out of bounds")
    if int(cw.get("period_seconds", 300)) not in range(60, 3601, 60):
        raise InvalidConfigurationError("CloudWatch period is out of bounds")
    filters = raw.get("resource_filters") or {}
    if set(filters) - {"include_tags", "exclude_tags"}:
        raise InvalidConfigurationError("unknown resource filter")
    if sum(len(v) for group in filters.values() for v in group.values()) > 100:
        raise InvalidConfigurationError("too many tag filters")
    if len(raw.get("ownership_tag_keys") or ()) > 20:
        raise InvalidConfigurationError("too many ownership tag keys")
    options = raw.get("service_options") or {}
    if not isinstance(options, Mapping) or not set(options) <= SERVICES:
        raise InvalidConfigurationError("unsupported service_options service")
    allowed_options = {
        "s3": {
            "include_buckets",
            "prefix_assets",
            "maximum_prefix_samples",
            "maximum_prefix_pages",
            "stale_after_seconds",
        },
        "lambda": {"include_function_patterns"},
        "sagemaker": {
            "include_training_jobs",
            "include_processing_jobs",
            "include_transform_jobs",
            "include_pipeline_executions",
            "include_endpoints",
            "history_lookback_seconds",
            "history_overlap_seconds",
            "maximum_history_items",
        },
        "mwaa": {"collect_environment_metrics"},
        "redshift": {
            "include_query_summaries",
            "query_history_lookback_seconds",
            "history_overlap_seconds",
            "maximum_query_summaries",
        },
        "redshift-serverless": {
            "include_query_summaries",
            "query_history_lookback_seconds",
            "history_overlap_seconds",
            "maximum_query_summaries",
        },
        "kinesis": {
            "include_streams",
            "include_shards",
            "include_metrics",
            "include_shard_metrics_if_enabled",
            "maximum_streams",
            "maximum_stream_pages",
            "maximum_shards_per_stream",
            "maximum_shard_pages",
        },
        "sqs": {
            "include_queues",
            "include_metrics",
            "include_dlq_relationships",
            "maximum_queues",
            "maximum_queue_pages",
        },
    }
    for service, value in options.items():
        if not isinstance(value, Mapping) or set(value) - allowed_options.get(service, set()):
            raise InvalidConfigurationError(f"unknown {service} service option")
    s3 = options.get("s3", {})
    if len(s3.get("include_buckets", ())) > 100 or len(s3.get("prefix_assets", ())) > 100:
        raise InvalidConfigurationError("too many S3 selections")
    if not 1 <= int(s3.get("maximum_prefix_samples", 100)) <= 1000:
        raise InvalidConfigurationError("S3 prefix sample limit is out of bounds")
    if not 1 <= int(s3.get("maximum_prefix_pages", 10)) <= 100:
        raise InvalidConfigurationError("S3 prefix page limit is out of bounds")
    for asset in s3.get("prefix_assets", ()):
        if (
            not isinstance(asset, Mapping)
            or set(asset) != {"bucket", "prefix"}
            or not asset.get("bucket")
            or not asset.get("prefix")
        ):
            raise InvalidConfigurationError("S3 prefix assets require only bucket and non-empty prefix")
    lam = options.get("lambda", {})
    if len(lam.get("include_function_patterns", ())) > 100:
        raise InvalidConfigurationError("too many Lambda function patterns")
    for service in ("sagemaker", "redshift", "redshift-serverless"):
        value = options.get(service, {})
        lookback = int(value.get("history_lookback_seconds", value.get("query_history_lookback_seconds", 86400)))
        if not 300 <= lookback <= 2592000:
            raise InvalidConfigurationError(f"{service} history lookback is out of bounds")
        if not 1 <= int(value.get("maximum_history_items", value.get("maximum_query_summaries", 200))) <= 1000:
            raise InvalidConfigurationError(f"{service} history item limit is out of bounds")
    kin = options.get("kinesis", {})
    if len(kin.get("include_streams", ())) > 500:
        raise InvalidConfigurationError("too many Kinesis stream selections")
    for key, default, maximum in (
        ("maximum_streams", 500, 1000),
        ("maximum_stream_pages", 50, 100),
        ("maximum_shards_per_stream", 1000, 10000),
        ("maximum_shard_pages", 100, 1000),
    ):
        if not 1 <= int(kin.get(key, default)) <= maximum:
            raise InvalidConfigurationError(f"Kinesis {key} is out of bounds")
    sqs = options.get("sqs", {})
    if len(sqs.get("include_queues", ())) > 1000:
        raise InvalidConfigurationError("too many SQS queue selections")
    for key, default, maximum in (("maximum_queues", 1000, 1000), ("maximum_queue_pages", 100, 100)):
        if not 1 <= int(sqs.get(key, default)) <= maximum:
            raise InvalidConfigurationError(f"SQS {key} is out of bounds")
    endpoint = raw.get("sts_endpoint_url")
    if endpoint and not str(endpoint).startswith(("http://localhost", "http://127.0.0.1")):
        raise InvalidConfigurationError("custom STS endpoints are test-only")
    return AwsConfiguration(str(account) if account else None, regions, services, raw)
