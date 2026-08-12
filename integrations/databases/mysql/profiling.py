from .dialect import quote_identifier

_ALLOWED = {"count", "null_count", "distinct_count", "min", "max", "min_length", "max_length"}


def profiling_statement(policy):
    metrics = policy.get("metrics", ["count"])
    if not metrics or not set(metrics) <= _ALLOWED:
        raise ValueError("invalid_configuration")
    schema, table = quote_identifier(policy["schema"]), quote_identifier(policy["table"])
    column = quote_identifier(policy["column"]) if policy.get("column") else None
    expressions = []
    for metric in metrics:
        if metric == "count":
            expressions.append("COUNT(*) AS `count`")
        elif not column:
            raise ValueError("invalid_configuration")
        elif metric == "null_count":
            expressions.append(f"SUM({column} IS NULL) AS `null_count`")
        elif metric == "distinct_count":
            expressions.append(f"COUNT(DISTINCT {column}) AS `distinct_count`")
        elif metric in {"min", "max"}:
            expressions.append(f"{metric.upper()}({column}) AS `{metric}`")
        else:
            expressions.append(f"{metric.split('_')[0].upper()}(CHAR_LENGTH({column})) AS `{metric}`")
    return f"SELECT {', '.join(expressions)} FROM {schema}.{table}"
