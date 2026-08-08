from ..normalisation import observation, safe, value
from .common import bounded

FIELDS = ("routine_id", "type_", "language", "created", "modified")


def collect(client, context, cfg, project, dataset):
    did = str(value(dataset, "dataset_id"))
    for x in bounded(
        client.invoke(
            "list_routines",
            f"{project.project_id}.{did}",
            read_mask="routineReference,routineType,language,creationTime,lastModifiedTime,arguments",
        ),
        cfg.limits["maximum_routines"],
        lambda y: value(y, "routine_id"),
    ):
        rid = str(value(x, "routine_id"))
        yield observation(
            context,
            project.project_id,
            str(value(dataset, "location", project.locations[0])),
            "routine",
            f"{did}.{rid}",
            rid,
            {**safe(x, FIELDS), "argument_count": len(value(x, "arguments", ()) or ())},
        )
