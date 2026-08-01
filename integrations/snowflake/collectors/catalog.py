from ..normalisation import resource, safe_row
from ..sql import SQL_TEMPLATES, execute_bounded


def collect(connection, context, cfg, parameters):
    limits = {
        "databases": cfg.maximum_databases,
        "schemas": cfg.maximum_schemas,
        "tables": cfg.maximum_objects,
        "columns": cfg.maximum_columns,
    }
    include = {name.upper() for name in cfg.include_databases}
    exclude = {name.upper() for name in cfg.exclude_schemas}
    seen = set()
    for family, limit in limits.items():
        for row in execute_bounded(connection, SQL_TEMPLATES[family], {"limit": limit}, batch_size=100):
            database = str(row.get("table_catalog") or row.get("catalog_name") or row.get("database_name") or "")
            schema = str(row.get("table_schema") or row.get("schema_name") or "")
            if (include and database.upper() not in include) or schema.upper() in exclude:
                continue
            native = str(row.get("database_id") or row.get("schema_id") or row.get("table_id"))
            if family == "columns":
                native += ":" + str(row.get("ordinal_position"))
            key = family, native
            if key in seen:
                continue
            seen.add(key)
            evidence = safe_row(row)
            if family == "tables":
                evidence["freshness_method"] = "metadata_last_altered"
            yield resource(
                row,
                context=context,
                account=cfg.account_identifier,
                family=family.rstrip("s"),
                native_id=native,
                name=str(
                    row.get("column_name")
                    or row.get("table_name")
                    or row.get("schema_name")
                    or row.get("database_name")
                    or native
                ),
                evidence=evidence,
            )
