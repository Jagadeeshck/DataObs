from packages.collectors.sdk.errors import IntegrationError

SAFE_ERROR_CODES = {
    "invalid_configuration",
    "dependency_unavailable",
    "authentication_failed",
    "token_expired",
    "key_rejected",
    "role_unavailable",
    "warehouse_unavailable",
    "account_unavailable",
    "access_denied",
    "object_not_found",
    "statement_timeout",
    "network_timeout",
    "connection_unavailable",
    "query_cancelled",
    "query_result_malformed",
    "provider_throttled",
    "checkpoint_conflict",
    "partial_collection_failure",
    "internal_collector_failure",
    "credential_reference_invalid",
    "credential_unavailable",
    "credential_expired",
    "credential_access_denied",
    "credential_format_invalid",
}


def safe_error(code: str, *, retryable: bool = False) -> IntegrationError:
    """Return a stable error without copying connector diagnostics."""
    selected = code if code in SAFE_ERROR_CODES else "internal_collector_failure"
    error = IntegrationError(f"Snowflake operation failed ({selected})")
    error.code = selected  # type: ignore[assignment]
    error.retryable = retryable  # type: ignore[assignment]
    return error


def map_connector_error(exc: BaseException) -> IntegrationError:
    errno = getattr(exc, "errno", None)
    if errno in {250001, 390100, 390144}:
        return safe_error("authentication_failed")
    if errno in {390112, 390114}:
        return safe_error("token_expired")
    if errno in {2003, 2043}:
        return safe_error("object_not_found")
    if errno in {3001, 604}:
        return safe_error("statement_timeout", retryable=True)
    return safe_error("connection_unavailable", retryable=True)
