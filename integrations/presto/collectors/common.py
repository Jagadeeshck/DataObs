from integrations.sql_engine import BoundedExecutor

from ..normalisation import resource


def execute(connection, registry, name, context, cfg, cluster, parameters=None):
    result = BoundedExecutor(
        registry,
        fetch_size=cfg.limits["fetch_size"],
        maximum_rows=cfg.limits["maximum_rows_per_statement"],
        maximum_pages=cfg.limits["maximum_pages"],
    ).execute(
        connection,
        name,
        parameters,
        deadline_seconds=min(context.remaining_seconds, cfg.limits["statement_timeout_seconds"]),
    )
    for row in result.rows:
        yield resource(
            context,
            cluster,
            registry.get(name).family,
            "|".join(str(x) for x in row[:3]),
            dict(zip(result.columns, row)),
        )
    if result.truncated:
        raise RuntimeError("result_truncated")
