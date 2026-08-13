from integrations.database.schema import structural_fingerprint

SENSITIVE_FIELDS = {
    "definition",
    "filter_definition",
    "masking_function",
    "computed_definition",
    "default_definition",
    "check_definition",
}


def safe_evidence(row):
    return {key: value for key, value in row.items() if key.lower() not in SENSITIVE_FIELDS}


def schema_fingerprint(rows):
    dynamic = {
        "approximate_rows",
        "row_count",
        "used_page_count",
        "reserved_page_count",
        "create_date",
        "metadata_change_time",
    }
    return structural_fingerprint(
        [{k: v for k, v in safe_evidence(row).items() if k.lower() not in dynamic} for row in rows]
    )
