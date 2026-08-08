from ..normalisation import observation, safe, value
from .common import bounded

FIELDS = (
    "dataset_id",
    "location",
    "created",
    "modified",
    "default_table_expiration_ms",
    "default_partition_expiration_ms",
    "is_case_insensitive",
    "max_time_travel_hours",
)


def collect(client, context, cfg, project):
    items = client.invoke("list_datasets", project=project.project_id)
    for x in bounded(
        items, cfg.limits["maximum_datasets_per_project"], lambda y: value(y, "dataset_id", value(y, "reference", y))
    ):
        did = str(value(x, "dataset_id"))
        if (project.include_datasets and did not in project.include_datasets) or did in project.exclude_datasets:
            continue
        yield observation(
            context,
            project.project_id,
            str(value(x, "location", project.locations[0])),
            "dataset",
            did,
            did,
            {
                **safe(x, FIELDS),
                "customer_managed_encryption_configured": bool(value(x, "default_encryption_configuration")),
                "visibility": "permission_filtered",
            },
        )
