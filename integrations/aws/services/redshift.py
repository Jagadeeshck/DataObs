from __future__ import annotations

import hashlib

from .common import observation, pages


def _hash(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16] if value is not None else None


def safe_query_summary(statement):
    """Return a deliberately SQL-free statement summary."""
    return {
        "query_id": statement.get("Id"),
        "status": statement.get("Status"),
        "start_timestamp": statement.get("CreatedAt"),
        "end_timestamp": statement.get("UpdatedAt"),
        "duration_ns": statement.get("Duration"),
        "rows_returned_count": statement.get("ResultRows"),
        "database_hash": _hash(statement.get("Database")),
        "user_hash": _hash(statement.get("DbUser")),
        "error_category": "query_failure" if statement.get("Status") in {"FAILED", "ABORTED"} else None,
    }


def collect(client, context, cfg, account, region):
    for cluster in pages(client, "describe_clusters", "Clusters"):
        identifier = cluster.get("ClusterIdentifier")
        arn = cluster.get("ClusterNamespaceArn") or f"arn:aws:redshift:{region}:{account}:cluster:{identifier}"
        safe = {
            "node_type": cluster.get("NodeType"),
            "node_count": cluster.get("NumberOfNodes"),
            "cluster_status": cluster.get("ClusterStatus"),
            "database_count": len(cluster.get("DBGroups", ())) or None,
            "encrypted": cluster.get("Encrypted"),
            "enhanced_vpc_routing": cluster.get("EnhancedVpcRouting"),
            "publicly_accessible": cluster.get("PubliclyAccessible"),
            "automated_snapshot_retention": cluster.get("AutomatedSnapshotRetentionPeriod"),
            "maintenance_window": cluster.get("PreferredMaintenanceWindow"),
            "availability_zone": cluster.get("AvailabilityZone"),
            "multi_az": cluster.get("MultiAZ"),
            "version": cluster.get("ClusterVersion"),
            "creation_timestamp": cluster.get("ClusterCreateTime"),
        }
        yield observation(
            context, cfg, account, region, "redshift", "cluster", arn, identifier, safe, cluster.get("Tags", ())
        )


def collect_query_summaries(data_client, context, cfg, account, region):
    """Optional Data API inventory; callers isolate permission failures from clusters."""
    options = (cfg.raw.get("service_options") or {}).get("redshift", {})
    if not options.get("include_query_summaries"):
        return
    limit = int(options.get("maximum_query_summaries", 200))
    seen = set()
    for item in pages(
        data_client,
        "list_statements",
        "Statements",
        token="NextToken",
        output_token="NextToken",
        MaxResults=min(100, limit),
    ):
        query_id = item.get("Id")
        if not query_id or query_id in seen or len(seen) >= limit:
            continue
        seen.add(query_id)
        yield observation(
            context, cfg, account, region, "redshift", "query_summary", query_id, query_id, safe_query_summary(item)
        )
