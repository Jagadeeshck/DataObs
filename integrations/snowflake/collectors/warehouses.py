from ..normalisation import resource, safe_row
from ..sql import SQL_TEMPLATES, execute_bounded


def collect(connection, context, cfg, parameters):
    for family in ("warehouses", "resource_monitors"):
        for row in execute_bounded(connection, SQL_TEMPLATES[family], parameters, batch_size=100):
            native = str(row.get("warehouse_id") or row.get("id"))
            yield resource(
                row,
                context=context,
                account=cfg.account_identifier,
                family=family.rstrip("s"),
                native_id=native,
                name=str(row.get("warehouse_name") or row.get("name") or native),
                evidence=safe_row(row),
            )
