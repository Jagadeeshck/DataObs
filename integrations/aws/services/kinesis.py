"""Bounded, payload-blind Amazon Kinesis Data Streams evidence collection."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.collectors.sdk import PartialFailure

from ..cloudwatch import KINESIS_METRICS, CloudWatchAdapter
from ..errors import map_aws_error
from .common import observation


def _envelope(context, account, region, kind, native_id, name, *, parent=None):
    value = {
        "tenant_id": context.tenant_id,
        "environment": context.attributes.get("environment", "unknown"),
        "messaging_system": "kinesis",
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
    if parent:
        value["parent_resource_id"] = parent
    return value


def _metrics(client, cfg, resource_id, stream_name):
    cw = cfg.raw.get("cloudwatch") or {}
    return CloudWatchAdapter(
        client,
        lookback_seconds=int(cw.get("lookback_seconds", 900)),
        period_seconds=int(cw.get("period_seconds", 300)),
        maximum_queries=min(100, len(KINESIS_METRICS)),
    ).collect(resource_id, "AWS/Kinesis", {"StreamName": stream_name}, KINESIS_METRICS)


def collect(client, context, cfg, account, region, *, cloudwatch_client=None):
    options = (cfg.raw.get("service_options") or {}).get("kinesis", {})
    selected = set(options.get("include_streams") or ())
    maximum_streams = int(options.get("maximum_streams", 500))
    maximum_pages = int(options.get("maximum_stream_pages", 50))
    names, start, inventory_truncated = [], None, False
    for _ in range(maximum_pages):
        kwargs = {"Limit": min(100, maximum_streams - len(names))}
        if start:
            kwargs["ExclusiveStartStreamName"] = start
        response = client.list_streams(**kwargs)
        page_names = [str(name) for name in response.get("StreamNames", ())]
        for name in page_names:
            if len(names) >= maximum_streams:
                inventory_truncated = True
                break
            if not selected or name in selected:
                names.append(name)
        more = bool(response.get("HasMoreStreams"))
        if len(names) >= maximum_streams:
            inventory_truncated = inventory_truncated or more
            break
        if not more or not page_names:
            break
        start = page_names[-1]
    else:
        inventory_truncated = True

    for stream_name in names:
        try:
            summary = client.describe_stream_summary(StreamName=stream_name).get("StreamDescriptionSummary", {})
            arn = str(summary.get("StreamARN") or stream_name)
            tags = client.list_tags_for_stream(StreamARN=arn, Limit=50).get("Tags", ())
        except Exception as exc:
            safe = map_aws_error(exc)
            yield PartialFailure(
                "metadata_collection", str(safe.code), "kinesis stream metadata unavailable", safe.retryable
            )
            continue

        shards, token, shard_truncated = [], None, False
        if options.get("include_shards", True):
            try:
                maximum_shards = int(options.get("maximum_shards_per_stream", 1000))
                for _ in range(int(options.get("maximum_shard_pages", 100))):
                    kwargs = {"StreamARN": arn, "MaxResults": min(1000, maximum_shards - len(shards))}
                    if token:
                        kwargs = {"NextToken": token, "MaxResults": min(1000, maximum_shards - len(shards))}
                    response = client.list_shards(**kwargs)
                    for shard in response.get("Shards", ()):
                        if len(shards) >= maximum_shards:
                            shard_truncated = True
                            break
                        shards.append(shard)
                    token = response.get("NextToken")
                    if len(shards) >= maximum_shards or not token:
                        shard_truncated = shard_truncated or bool(token)
                        break
                else:
                    shard_truncated = bool(token)
            except Exception as exc:
                safe = map_aws_error(exc)
                shard_truncated = True
                yield PartialFailure(
                    "metadata_collection", str(safe.code), "kinesis shard topology unavailable", safe.retryable
                )

        encryption_type = "kms" if summary.get("EncryptionType") == "KMS" else "none"
        mode = (summary.get("StreamModeDetails") or {}).get("StreamMode", "unknown").lower()
        monitoring = sorted(
            {metric for item in summary.get("EnhancedMonitoring", ()) for metric in item.get("ShardLevelMetrics", ())}
        )
        envelope = _envelope(context, account, region, "stream", arn, stream_name)
        safe_evidence = envelope | {
            "stream_status": summary.get("StreamStatus"),
            "stream_mode": mode,
            "retention_period_hours": summary.get("RetentionPeriodHours"),
            "stream_creation_time": summary.get("StreamCreationTimestamp"),
            "open_shard_count": summary.get("OpenShardCount"),
            "consumer_count": summary.get("ConsumerCount"),
            "enhanced_monitoring_categories": monitoring,
            "encrypted": encryption_type == "kms",
            "encryption_type": encryption_type,
            "result_truncated": inventory_truncated or shard_truncated,
        }
        stream = observation(context, cfg, account, region, "kinesis", "stream", arn, stream_name, safe_evidence, tags)
        if stream:
            yield stream
            if options.get("include_metrics", True) and cloudwatch_client is not None:
                try:
                    yield from _metrics(cloudwatch_client, cfg, stream.canonical_id, stream_name)
                except Exception as exc:
                    safe = map_aws_error(exc)
                    yield PartialFailure(
                        "metric_collection", str(safe.code), "kinesis metrics unavailable", safe.retryable
                    )
        for shard in shards:
            shard_id = str(shard.get("ShardId", ""))
            if not shard_id:
                continue
            shard_native_id = f"{arn}/{shard_id}"
            shard_envelope = _envelope(context, account, region, "shard", shard_native_id, shard_id, parent=arn)
            # Sequence/hash ranges are deliberately inspected only to derive state and are never retained.
            shard_safe = shard_envelope | {
                "shard_id": shard_id,
                "parent_shard_id": shard.get("ParentShardId"),
                "adjacent_parent_shard_id": shard.get("AdjacentParentShardId"),
                "state": "closed" if (shard.get("SequenceNumberRange") or {}).get("EndingSequenceNumber") else "open",
                "result_truncated": shard_truncated,
            }
            yield observation(context, cfg, account, region, "kinesis", "shard", shard_native_id, shard_id, shard_safe)
