from ..normalisation import observation, safe, value
from .common import bounded

FIELDS = ("table_id", "table_type", "created", "modified", "expires", "num_rows", "num_bytes", "partitioning_type")


def _columns(schema, parent="", depth=0):
    for pos, f in enumerate(schema or ()):
        name = str(value(f, "name"))
        path = f"{parent}.{name}" if parent else name
        yield path, {
            "field_name": name,
            "ordinal_position": pos,
            "bigquery_type": value(f, "field_type"),
            "mode": value(f, "mode"),
            "nullable": value(f, "mode") != "REQUIRED",
            "repeated": value(f, "mode") == "REPEATED",
            "nesting_depth": depth,
            "parent_field_path": parent or None,
            "maximum_length": value(f, "max_length"),
            "precision": value(f, "precision"),
            "scale": value(f, "scale"),
        }
        yield from _columns(value(f, "fields", ()), path, depth + 1)


def collect(client, context, cfg, project, dataset):
    did = str(value(dataset, "dataset_id"))
    items = client.invoke("list_tables", f"{project.project_id}.{did}")
    for x in bounded(items, cfg.limits["maximum_tables_per_dataset"], lambda y: value(y, "table_id")):
        tid = str(value(x, "table_id"))
        detail = (
            client.invoke("get_table", f"{project.project_id}.{did}.{tid}")
            if cfg.metadata.get("include_columns", False)
            else x
        )
        evidence = {
            **safe(detail, FIELDS),
            "partitioning_configured": bool(value(detail, "time_partitioning") or value(detail, "range_partitioning")),
            "clustering_configured": bool(value(detail, "clustering_fields")),
            "clustering_column_count": len(value(detail, "clustering_fields", ()) or ()),
            "customer_managed_encryption_configured": bool(value(detail, "encryption_configuration")),
            "streaming_buffer_present": bool(value(detail, "streaming_buffer")),
            "freshness_method": "bigquery_table_last_modified_metadata",
        }
        yield observation(
            context,
            project.project_id,
            str(value(dataset, "location", project.locations[0])),
            "table",
            f"{did}.{tid}",
            tid,
            evidence,
        )
        if cfg.metadata.get("include_columns", False):
            for path, col in list(_columns(value(detail, "schema", ())))[: cfg.limits["maximum_columns"]]:
                yield observation(
                    context,
                    project.project_id,
                    str(value(dataset, "location", project.locations[0])),
                    "column",
                    f"{did}.{tid}.{path}",
                    path,
                    {**col, "table_id": f"{did}.{tid}"},
                )
