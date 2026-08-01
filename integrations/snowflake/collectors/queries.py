from ..normalisation import resource, safe_row
from ..sql import SQL_TEMPLATES, execute_bounded


def collect(connection, context, cfg, parameters):
    for row in execute_bounded(connection, SQL_TEMPLATES["query_history"], parameters, batch_size=100):
        evidence = safe_row(row)
        code = evidence.pop("error_code", None)
        evidence["error_category"] = "provider_error" if code else "none"
        query_id = str(row.get("query_id"))
        yield resource(
            row,
            context=context,
            account=cfg.account_identifier,
            family="query_history",
            native_id=query_id,
            name="Snowflake query execution",
            evidence=evidence,
        )
