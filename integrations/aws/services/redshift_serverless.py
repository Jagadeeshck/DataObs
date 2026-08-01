from .common import observation, pages


def _tags(client, arn):
    try:
        return client.list_tags_for_resource(resourceArn=arn).get("tags", ())
    except Exception:
        return ()


def collect(client, context, cfg, account, region):
    for namespace in pages(
        client, "list_namespaces", "namespaces", token="nextToken", output_token="nextToken", maxResults=100
    ):
        arn, name = namespace.get("namespaceArn") or namespace.get("namespaceId"), namespace.get("namespaceName")
        safe = {
            "status": namespace.get("status"),
            "creation_timestamp": namespace.get("creationDate"),
            "encryption_configured": bool(namespace.get("kmsKeyId")),
        }
        yield observation(
            context, cfg, account, region, "redshift-serverless", "namespace", arn, name, safe, _tags(client, arn)
        )
    for workgroup in pages(
        client, "list_workgroups", "workgroups", token="nextToken", output_token="nextToken", maxResults=100
    ):
        arn, name = workgroup.get("workgroupArn") or workgroup.get("workgroupId"), workgroup.get("workgroupName")
        config = workgroup.get("configParameters", ())
        safe = {
            "status": workgroup.get("status"),
            "base_capacity": workgroup.get("baseCapacity"),
            "maximum_capacity": workgroup.get("maxCapacity"),
            "enhanced_vpc_routing": workgroup.get("enhancedVpcRouting"),
            "publicly_accessible": workgroup.get("publiclyAccessible"),
            "creation_timestamp": workgroup.get("creationDate"),
        }
        # configParameters and endpoints are intentionally discarded.
        del config
        yield observation(
            context, cfg, account, region, "redshift-serverless", "workgroup", arn, name, safe, _tags(client, arn)
        )
