from integrations.database.schema import structural_fingerprint

SENSITIVE_FIELDS = {
    "data_default",
    "low_value",
    "high_value",
    "histogram",
    "search_condition",
    "search_condition_vc",
    "text",
    "text_vc",
    "query",
    "query_len",
    "column_expression",
}
DYNAMIC_FIELDS = {"num_rows", "approximate_rows", "last_analyzed", "observed_at"}


def safe_evidence(row):
    return {k: v for k, v in row.items() if k.lower() not in SENSITIVE_FIELDS}


def schema_fingerprint(rows):
    return structural_fingerprint(
        [{k: v for k, v in safe_evidence(r).items() if k.lower() not in DYNAMIC_FIELDS} for r in rows]
    )
