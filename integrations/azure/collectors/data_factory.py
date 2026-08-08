from ..normalisation import observation, resource_id, safe, value
from ..pagination import bounded


def collect(client, context, cfg, item):
    rg, name = item["resource_group"], item["factory_name"]
    raw = client.invoke("factory_get", rg, name)
    rid = resource_id(cfg, rg, "microsoft.datafactory", "factories", name)
    region = value(raw, "location", "global")
    yield observation(
        context,
        cfg,
        region,
        "data_factory",
        "adf.factory",
        rid,
        name,
        {
            "resource_group": rg,
            "factory_name": name,
            **safe(raw, ("provisioning_state", "public_network_access", "create_time")),
            "managed_identity_present": value(raw, "identity") is not None,
            "git_integration_configured": value(raw, "repo_configuration") is not None,
        },
    )
    if item.get("include_pipeline_metadata", True):
        for p in bounded(
            client.invoke("pipeline_list", rg, name),
            cfg.limits["maximum_pages"],
            cfg.limits["maximum_observations"],
            lambda x: value(x, "name"),
            context,
        ):
            acts = value(p, "activities", ()) or ()
            props = {
                "factory_canonical_id": rid,
                "pipeline_name": value(p, "name"),
                "activity_count": len(acts),
                "parameter_count": len(value(p, "parameters", {}) or {}),
                "variable_count": len(value(p, "variables", {}) or {}),
                "concurrency": value(p, "concurrency"),
                "annotation_count": len(value(p, "annotations", ()) or ()),
                "activity_summaries": [
                    {
                        "activity_type": type(a).__name__,
                        "dependency_count": len(value(a, "depends_on", ()) or ()),
                        "retry_configured": bool(value(value(a, "policy", {}), "retry")),
                        "timeout_configured": bool(value(value(a, "policy", {}), "timeout")),
                    }
                    for a in acts
                ],
            }
            yield observation(
                context,
                cfg,
                region,
                "data_factory",
                "adf.pipeline",
                rid + "/pipelines/" + value(p, "name"),
                value(p, "name"),
                props,
            )
    if item.get("include_trigger_metadata", True):
        for t in bounded(
            client.invoke("trigger_list", rg, name),
            cfg.limits["maximum_pages"],
            cfg.limits["maximum_observations"],
            lambda x: value(x, "name"),
            context,
        ):
            yield observation(
                context,
                cfg,
                region,
                "data_factory",
                "adf.trigger",
                rid + "/triggers/" + value(t, "name"),
                value(t, "name"),
                {
                    "trigger_name": value(t, "name"),
                    "trigger_type": type(value(t, "properties", t)).__name__,
                    "runtime_state": value(t, "runtime_state"),
                    "pipeline_reference_count": len(value(t, "pipelines", ()) or ()),
                },
            )
