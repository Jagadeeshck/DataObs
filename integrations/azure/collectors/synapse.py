from ..normalisation import observation, resource_id, safe, value
from ..pagination import bounded


def collect(client, context, cfg, item):
    rg, name = item["resource_group"], item["workspace_name"]
    raw = client.invoke("workspace_get", rg, name)
    wid = resource_id(cfg, rg, "microsoft.synapse", "workspaces", name)
    region = value(raw, "location", "global")
    yield observation(
        context,
        cfg,
        region,
        "synapse",
        "synapse.workspace",
        wid,
        name,
        {
            "resource_group": rg,
            "workspace_name": name,
            **safe(raw, ("provisioning_state", "public_network_access")),
            "managed_virtual_network_configured": bool(value(raw, "managed_virtual_network")),
            "managed_identity_present": value(raw, "identity") is not None,
        },
    )
    if item.get("include_sql_pools", True):
        for p in bounded(
            client.invoke("sql_pool_list", rg, name),
            cfg.limits["maximum_pages"],
            cfg.limits["maximum_observations"],
            lambda x: value(x, "name"),
            context,
        ):
            yield observation(
                context,
                cfg,
                region,
                "synapse",
                "synapse.sql_pool",
                wid + "/sqlPools/" + value(p, "name"),
                value(p, "name"),
                {
                    "workspace_canonical_id": wid,
                    "pool_name": value(p, "name"),
                    **safe(p, ("status", "creation_date", "collation")),
                    "sku_name": value(value(p, "sku", {}), "name"),
                    "capacity": value(value(p, "sku", {}), "capacity"),
                },
            )
    if item.get("include_spark_pools", True):
        for p in bounded(
            client.invoke("spark_pool_list", rg, name),
            cfg.limits["maximum_pages"],
            cfg.limits["maximum_observations"],
            lambda x: value(x, "name"),
            context,
        ):
            scale = value(p, "auto_scale", {}) or {}
            pause = value(p, "auto_pause", {}) or {}
            yield observation(
                context,
                cfg,
                region,
                "synapse",
                "synapse.spark_pool",
                wid + "/bigDataPools/" + value(p, "name"),
                value(p, "name"),
                {
                    "workspace_canonical_id": wid,
                    "pool_name": value(p, "name"),
                    **safe(p, ("provisioning_state", "spark_version", "node_size", "node_size_family")),
                    "auto_scale_enabled": value(scale, "enabled"),
                    "minimum_node_count": value(scale, "min_node_count"),
                    "maximum_node_count": value(scale, "max_node_count"),
                    "auto_pause_enabled": value(pause, "enabled"),
                    "delay_in_minutes": value(pause, "delay_in_minutes"),
                    "dynamic_executor_allocation_configured": value(p, "dynamic_executor_allocation") is not None,
                },
            )
    if item.get("include_pipeline_metadata", True):
        for p in bounded(
            client.invoke("synapse_pipeline_list", rg, name),
            cfg.limits["maximum_pages"],
            cfg.limits["maximum_observations"],
            lambda x: value(x, "name"),
            context,
        ):
            yield observation(
                context,
                cfg,
                region,
                "synapse",
                "synapse.pipeline",
                wid + "/pipelines/" + value(p, "name"),
                value(p, "name"),
                {
                    "workspace_canonical_id": wid,
                    "pipeline_name": value(p, "name"),
                    "activity_count": len(value(p, "activities", ()) or ()),
                    "parameter_count": len(value(p, "parameters", {}) or {}),
                    "variable_count": len(value(p, "variables", {}) or {}),
                    "concurrency": value(p, "concurrency"),
                },
            )
