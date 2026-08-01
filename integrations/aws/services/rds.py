from .common import observation, pages


def collect(client, context, cfg, account, region):
    for method, key, kind, id_key, name_key in (
        ("describe_db_instances", "DBInstances", "db_instance", "DBInstanceArn", "DBInstanceIdentifier"),
        ("describe_db_clusters", "DBClusters", "db_cluster", "DBClusterArn", "DBClusterIdentifier"),
    ):
        for item in pages(client, method, key):
            safe = {
                k: item.get(k)
                for k in (
                    "Engine",
                    "EngineVersion",
                    "DBInstanceClass",
                    "Status",
                    "DBInstanceStatus",
                    "MultiAZ",
                    "AvailabilityZone",
                    "AllocatedStorage",
                    "StorageType",
                    "StorageEncrypted",
                    "DeletionProtection",
                    "PubliclyAccessible",
                    "BackupRetentionPeriod",
                )
                if k in item
            }
            arn = item.get(id_key) or item.get(name_key)
            tags = client.list_tags_for_resource(ResourceName=arn).get("TagList", []) if arn else []
            value = observation(context, cfg, account, region, "rds", kind, arn, item.get(name_key, arn), safe, tags)
            if value:
                yield value
