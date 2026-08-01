from __future__ import annotations

from datetime import datetime, timezone

from .common import observation


def _optional(client, method, **kwargs):
    try:
        return getattr(client, method)(**kwargs)
    except Exception:
        # Optional bucket controls commonly return AccessDenied or a not-configured error.
        return None


def collect(client, context, cfg, account, region):
    options = (cfg.raw.get("service_options") or {}).get("s3", {})
    selected = set(options.get("include_buckets") or ())
    for bucket in client.list_buckets().get("Buckets", ())[:1000]:
        name = bucket.get("Name")
        if not name or (selected and name not in selected):
            continue
        location = _optional(client, "get_bucket_location", Bucket=name) or {}
        bucket_region = location.get("LocationConstraint") or "us-east-1"
        if bucket_region == "EU":
            bucket_region = "eu-west-1"
        if bucket_region != region:
            continue
        versioning = _optional(client, "get_bucket_versioning", Bucket=name) or {}
        encryption = _optional(client, "get_bucket_encryption", Bucket=name)
        public = _optional(client, "get_public_access_block", Bucket=name)
        lock = _optional(client, "get_object_lock_configuration", Bucket=name)
        lifecycle = _optional(client, "get_bucket_lifecycle_configuration", Bucket=name)
        replication = _optional(client, "get_bucket_replication", Bucket=name)
        logging = _optional(client, "get_bucket_logging", Bucket=name) or {}
        tag_response = _optional(client, "get_bucket_tagging", Bucket=name) or {}
        safe = {
            "creation_timestamp": bucket.get("CreationDate"),
            "versioning_state": versioning.get("Status", "disabled"),
            "default_encryption_state": "configured" if encryption else "unavailable",
            "public_access_block_state": "configured" if public else "unavailable",
            "object_lock_state": (lock or {})
            .get("ObjectLockConfiguration", {})
            .get("ObjectLockEnabled", "unavailable"),
            "lifecycle_rule_count": len((lifecycle or {}).get("Rules", ())),
            "replication_configured": bool(replication),
            "logging_configured": bool(logging.get("LoggingEnabled")),
        }
        yield observation(
            context,
            cfg,
            account,
            region,
            "s3",
            "bucket",
            f"arn:aws:s3:::{name}",
            name,
            safe,
            tag_response.get("TagSet", ()),
        )

    maximum = int(options.get("maximum_prefix_samples", 100))
    max_pages = int(options.get("maximum_prefix_pages", 10))
    now = datetime.now(timezone.utc)
    for asset in options.get("prefix_assets", ()):
        bucket, prefix = str(asset["bucket"]), str(asset["prefix"])
        count = total = 0
        latest = None
        token = None
        truncated = False
        for page_number in range(max_pages):
            kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": min(1000, maximum - count)}
            if token:
                kwargs["ContinuationToken"] = token
            response = client.list_objects_v2(**kwargs)
            for item in response.get("Contents", ()):
                if count >= maximum:
                    truncated = True
                    break
                count += 1
                total += int(item.get("Size", 0))
                modified = item.get("LastModified")
                latest = modified if modified and (latest is None or modified > latest) else latest
            token = response.get("NextContinuationToken")
            truncated = truncated or bool(response.get("IsTruncated"))
            if not token or count >= maximum:
                break
        if token and page_number + 1 >= max_pages:
            truncated = True
        safe = {
            "configured_bucket": bucket,
            "configured_prefix": prefix,
            "latest_observed_object_modification_time": latest,
            "sampled_object_count": count,
            "sampled_total_bytes": total,
            "sample_truncated": truncated,
            "empty_prefix": count == 0,
            "freshness_age_seconds": max(0, int((now - latest).total_seconds())) if latest else None,
            "evidence_state": "partial" if truncated else "measured",
            "collection_confidence": 0.5 if truncated else 1.0,
        }
        # Prefix is explicitly approved configuration; no individual object key is retained.
        yield observation(context, cfg, account, region, "s3", "prefix_asset", f"{bucket}/{prefix}", prefix, safe)
