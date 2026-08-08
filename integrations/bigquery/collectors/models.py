from ..normalisation import observation, safe, value
from .common import bounded

FIELDS = ("model_id", "model_type", "created", "modified", "expires")


def collect(client, context, cfg, project, dataset):
    did = str(value(dataset, "dataset_id"))
    for x in bounded(
        client.invoke("list_models", f"{project.project_id}.{did}"),
        cfg.limits["maximum_models"],
        lambda y: value(y, "model_id"),
    ):
        mid = str(value(x, "model_id"))
        yield observation(
            context,
            project.project_id,
            str(value(dataset, "location", project.locations[0])),
            "model",
            f"{did}.{mid}",
            mid,
            safe(x, FIELDS),
        )
