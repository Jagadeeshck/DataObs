"""Bounded Amazon SQS metadata collection that never reads a message."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from packages.collectors.sdk import PartialFailure

from ..cloudwatch import SQS_METRICS, CloudWatchAdapter
from ..errors import map_aws_error
from .common import observation

ATTRIBUTE_NAMES = (
    "QueueArn",
    "VisibilityTimeout",
    "MaximumMessageSize",
    "MessageRetentionPeriod",
    "ApproximateNumberOfMessages",
    "ApproximateNumberOfMessagesNotVisible",
    "ApproximateNumberOfMessagesDelayed",
    "CreatedTimestamp",
    "LastModifiedTimestamp",
    "DelaySeconds",
    "ReceiveMessageWaitTimeSeconds",
    "FifoQueue",
    "ContentBasedDeduplication",
    "DeduplicationScope",
    "FifoThroughputLimit",
    "SqsManagedSseEnabled",
    "RedrivePolicy",
)


def _integer(attributes, name):
    value = attributes.get(name)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _boolean(attributes, name):
    value = attributes.get(name)
    return None if value is None else str(value).lower() == "true"


def _redrive(value):
    if not value:
        return None
    try:
        parsed = json.loads(value)
        arn = parsed.get("deadLetterTargetArn")
        count = int(parsed.get("maxReceiveCount"))
        if not arn or count < 1:
            return None
        return {"dead_letter_queue": str(arn), "max_receive_count": count, "relationship_type": "redrive"}
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _envelope(context, account, region, kind, native_id, name):
    return {
        "tenant_id": context.tenant_id,
        "environment": context.attributes.get("environment", "unknown"),
        "messaging_system": "sqs",
        "provider": "aws",
        "provider_account_scope": account,
        "cloud_region_or_location": region,
        "resource_kind": kind,
        "provider_resource_id": native_id,
        "name": name,
        "observed_at": datetime.now(timezone.utc),
        "data_status": "complete",
        "confidence": 1.0,
        "source_coverage": 1.0,
        "collection_method": "aws_api",
        "source_integration": context.integration_id,
        "schema_version": "v1",
    }


def _metrics(client, cfg, resource_id, queue_name):
    cw = cfg.raw.get("cloudwatch") or {}
    return CloudWatchAdapter(
        client,
        lookback_seconds=int(cw.get("lookback_seconds", 900)),
        period_seconds=int(cw.get("period_seconds", 300)),
        maximum_queries=min(100, len(SQS_METRICS)),
    ).collect(resource_id, "AWS/SQS", {"QueueName": queue_name}, SQS_METRICS)


def collect(client, context, cfg, account, region, *, cloudwatch_client=None):
    options = (cfg.raw.get("service_options") or {}).get("sqs", {})
    selected = set(options.get("include_queues") or ())
    maximum = int(options.get("maximum_queues", 1000))
    urls, token, truncated = [], None, False
    for _ in range(int(options.get("maximum_queue_pages", 100))):
        kwargs = {"MaxResults": min(1000, maximum - len(urls))}
        if token:
            kwargs["NextToken"] = token
        response = client.list_queues(**kwargs)
        for url in response.get("QueueUrls", ()):
            name = urlparse(str(url)).path.rsplit("/", 1)[-1]
            if len(urls) >= maximum:
                truncated = True
                break
            if not selected or name in selected or str(url) in selected:
                urls.append(str(url))
        token = response.get("NextToken")
        if len(urls) >= maximum or not token:
            truncated = truncated or bool(token)
            break
    else:
        truncated = bool(token)

    gathered = []
    for url in urls:
        try:
            attrs = client.get_queue_attributes(QueueUrl=url, AttributeNames=list(ATTRIBUTE_NAMES)).get(
                "Attributes", {}
            )
            tags = client.list_queue_tags(QueueUrl=url).get("Tags", {})
        except Exception as exc:
            safe = map_aws_error(exc)
            yield PartialFailure(
                "metadata_collection", str(safe.code), "sqs queue metadata unavailable", safe.retryable
            )
            continue
        name = urlparse(url).path.rsplit("/", 1)[-1]
        arn = str(attrs.get("QueueArn") or url)
        gathered.append((url, name, arn, attrs, tags, _redrive(attrs.get("RedrivePolicy"))))

    visible_arns = {item[2] for item in gathered}
    dlq_arns = {
        item[5]["dead_letter_queue"] for item in gathered if item[5] and item[5]["dead_letter_queue"] in visible_arns
    }
    for url, name, arn, attrs, tags, redrive in gathered:
        kind = "dead_letter_queue" if arn in dlq_arns else "queue"
        envelope = _envelope(context, account, region, kind, arn, name)
        relationship = None
        if options.get("include_dlq_relationships", True) and redrive and redrive["dead_letter_queue"] in visible_arns:
            relationship = {"source_queue": arn} | redrive
        safe_evidence = envelope | {
            "fifo": bool(_boolean(attrs, "FifoQueue")),
            "content_based_deduplication": _boolean(attrs, "ContentBasedDeduplication"),
            "visibility_timeout_seconds": _integer(attrs, "VisibilityTimeout"),
            "delay_seconds": _integer(attrs, "DelaySeconds"),
            "retention_seconds": _integer(attrs, "MessageRetentionPeriod"),
            "maximum_message_size_bytes": _integer(attrs, "MaximumMessageSize"),
            "managed_encryption_enabled": _boolean(attrs, "SqsManagedSseEnabled"),
            "created_timestamp": _integer(attrs, "CreatedTimestamp"),
            "last_modified_timestamp": _integer(attrs, "LastModifiedTimestamp"),
            "backlog_messages": _integer(attrs, "ApproximateNumberOfMessages"),
            "inflight_messages": _integer(attrs, "ApproximateNumberOfMessagesNotVisible"),
            "delayed_messages": _integer(attrs, "ApproximateNumberOfMessagesDelayed"),
            "measurement_method": "provider_approximate",
            "dlq_relationship": relationship,
            "result_truncated": truncated,
        }
        queue = observation(context, cfg, account, region, "sqs", kind, arn, name, safe_evidence, tags)
        if queue:
            yield queue
            if options.get("include_metrics", True) and cloudwatch_client is not None:
                try:
                    yield from _metrics(cloudwatch_client, cfg, queue.canonical_id, name)
                except Exception as exc:
                    safe = map_aws_error(exc)
                    yield PartialFailure("metric_collection", str(safe.code), "sqs metrics unavailable", safe.retryable)
