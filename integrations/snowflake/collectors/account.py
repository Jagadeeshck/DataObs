from ..normalisation import resource, safe_row
from ..sql import SQL_TEMPLATES, execute_bounded


def collect(connection, context, cfg, parameters):
    for row in execute_bounded(connection, SQL_TEMPLATES["account"], {"limit": 1}, batch_size=1):
        yield resource(
            row,
            context=context,
            account=cfg.account_identifier,
            family="account",
            native_id="account",
            name="Snowflake account",
            evidence=safe_row(row),
        )
