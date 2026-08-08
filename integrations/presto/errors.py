from packages.collectors.sdk.errors import IntegrationError

CODES = (
    "invalid_configuration",
    "dependency_unavailable",
    "client_incompatible",
    "credential_reference_invalid",
    "credential_unavailable",
    "authentication_failed",
    "tls_validation_failed",
    "coordinator_unavailable",
    "access_denied",
    "catalog_unavailable",
    "schema_unavailable",
    "statement_timeout",
    "statement_cancelled",
    "server_busy",
    "result_truncated",
    "result_malformed",
    "query_history_gap",
    "unsupported_server_version",
    "unsupported_metadata_shape",
    "checkpoint_conflict",
    "partial_collection_failure",
    "internal_collector_failure",
)


def safe_error(exc):
    text = str(exc).lower()
    code = next((item for item in CODES if item in text), "server_busy" if "503" in text else "coordinator_unavailable")
    error = IntegrationError("Presto collection unavailable")
    error.code = code
    error.retryable = code in {"coordinator_unavailable", "server_busy", "statement_timeout", "statement_cancelled"}
    return error
