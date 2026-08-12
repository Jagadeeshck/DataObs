from integrations.database.schema import structural_fingerprint

SENSITIVE_FIELDS = {
    "column_default",
    "generation_expression",
    "check_clause",
    "expression",
    "view_definition",
    "partition_expression",
    "subpartition_expression",
}


def safe_evidence(row):
    return {key: value for key, value in row.items() if key.lower() not in SENSITIVE_FIELDS}


def schema_fingerprint(rows):
    dynamic = {
        "approximate_rows",
        "data_bytes",
        "index_bytes",
        "cardinality",
        "create_time",
        "update_time",
        "check_time",
    }
    return structural_fingerprint(
        [{k: v for k, v in safe_evidence(row).items() if k.lower() not in dynamic} for row in rows]
    )
