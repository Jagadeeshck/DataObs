from .dialect import quote_identifier


def freshness_statement(policy):
    if policy.get("method") != "timestamp_column_max":
        raise ValueError("invalid_configuration")
    schema, table, column = (quote_identifier(policy[k]) for k in ("schema", "table", "column"))
    return f"SELECT MAX({column}) AS maximum_timestamp FROM {schema}.{table}"
