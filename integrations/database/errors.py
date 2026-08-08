ERROR_CODES = frozenset(
    {
        "invalid_configuration",
        "dependency_unavailable",
        "credential_reference_invalid",
        "credential_unavailable",
        "authentication_failed",
        "tls_validation_failed",
        "database_unavailable",
        "database_not_found",
        "access_denied",
        "statement_timeout",
        "statement_cancelled",
        "too_many_connections",
        "server_busy",
        "result_truncated",
        "metadata_unavailable",
        "profiling_not_enabled",
        "profiling_access_denied",
        "freshness_not_configured",
        "extension_unavailable",
        "checkpoint_conflict",
        "partial_collection_failure",
        "internal_collector_failure",
    }
)


def redacted_message(_: BaseException) -> str:
    return "PostgreSQL operation failed"
