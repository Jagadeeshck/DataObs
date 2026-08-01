from __future__ import annotations

from ..normalisation import SAFE_FIELDS, allowlist, observation, value
from ..pagination import Page, collect_pages


def _page(call, item_name, size):
    def fetch(token):
        response = call(page_token=token, max_results=size)
        return Page(tuple(value(response, item_name, ()) or ()), value(response, "next_page_token"))

    return fetch


def collect(client, context, cfg):
    uc, limits = cfg.unity_catalog, cfg.limits
    if not uc.get("enabled", True):
        return
    catalogs = collect_pages(
        _page(client.catalogs.list, "catalogs", limits["page_size"]),
        key=lambda x: str(value(x, "name")),
        maximum_pages=limits["maximum_pages"],
        maximum_results=int(uc.get("maximum_catalogs", 100)),
    )
    include = set(uc.get("include_catalogs", ()))
    for catalog in catalogs:
        name = str(value(catalog, "name"))
        if include and name not in include:
            continue
        yield observation(
            context,
            cfg.expected_workspace_id,
            cfg.cloud,
            "catalog",
            str(value(catalog, "id", name)),
            name,
            allowlist(catalog, SAFE_FIELDS["catalog"]),
        )
        schemas = collect_pages(
            _page(lambda **kw: client.schemas.list(catalog_name=name, **kw), "schemas", limits["page_size"]),
            key=lambda x: str(value(x, "full_name", value(x, "name"))),
            maximum_pages=limits["maximum_pages"],
            maximum_results=int(uc.get("maximum_schemas", 2000)),
        )
        for schema in schemas:
            schema_name = str(value(schema, "name"))
            if schema_name in set(uc.get("exclude_schemas", ())):
                continue
            yield observation(
                context,
                cfg.expected_workspace_id,
                cfg.cloud,
                "schema",
                f"{name}.{schema_name}",
                schema_name,
                allowlist(schema, SAFE_FIELDS["schema"]),
            )
            tables = collect_pages(
                _page(
                    lambda **kw: client.tables.list(catalog_name=name, schema_name=schema_name, **kw),
                    "tables",
                    limits["page_size"],
                ),
                key=lambda x: str(value(x, "full_name", value(x, "name"))),
                maximum_pages=limits["maximum_pages"],
                maximum_results=int(uc.get("maximum_tables", 50000)),
            )
            for table in tables:
                full = str(value(table, "full_name", f"{name}.{schema_name}.{value(table, 'name')}"))
                yield observation(
                    context,
                    cfg.expected_workspace_id,
                    cfg.cloud,
                    "table",
                    str(value(table, "table_id", full)),
                    str(value(table, "name")),
                    allowlist(table, SAFE_FIELDS["table"]),
                )
                if uc.get("include_columns", False):
                    detail = client.tables.get(full_name=full)
                    for index, column in enumerate(
                        tuple(value(detail, "columns", ()) or ())[: int(uc.get("maximum_columns", 200000))]
                    ):
                        safe = allowlist(
                            column,
                            (
                                "name",
                                "position",
                                "type_name",
                                "type_precision",
                                "type_scale",
                                "nullable",
                                "partition_index",
                            ),
                        )
                        yield observation(
                            context,
                            cfg.expected_workspace_id,
                            cfg.cloud,
                            "column",
                            f"{full}.{value(column, 'name')}",
                            str(value(column, "name")),
                            {**safe, "table_id": full, "ordinal_position": value(column, "position", index)},
                        )
            if uc.get("include_volumes", False):
                volumes = collect_pages(
                    _page(
                        lambda **kw: client.volumes.list(catalog_name=name, schema_name=schema_name, **kw),
                        "volumes",
                        limits["page_size"],
                    ),
                    key=lambda x: str(value(x, "full_name", value(x, "name"))),
                    maximum_pages=limits["maximum_pages"],
                    maximum_results=int(uc.get("maximum_volumes", 5000)),
                )
                for volume in volumes:
                    full = str(value(volume, "full_name", f"{name}.{schema_name}.{value(volume, 'name')}"))
                    yield observation(
                        context,
                        cfg.expected_workspace_id,
                        cfg.cloud,
                        "volume",
                        str(value(volume, "volume_id", full)),
                        str(value(volume, "name")),
                        allowlist(volume, SAFE_FIELDS["volume"]),
                    )
