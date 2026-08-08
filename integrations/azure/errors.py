from packages.collectors.sdk.errors import IntegrationError

ERROR_CODES = frozenset(
    {
        "invalid_configuration",
        "dependency_unavailable",
        "credential_reference_invalid",
        "credential_unavailable",
        "authentication_failed",
        "token_expired",
        "tenant_mismatch",
        "subscription_mismatch",
        "subscription_unavailable",
        "resource_group_unavailable",
        "resource_not_found",
        "access_denied",
        "rate_limited",
        "quota_exceeded",
        "request_timeout",
        "continuation_token_invalid",
        "continuation_token_loop",
        "history_window_invalid",
        "result_truncated",
        "result_malformed",
        "unsupported_feature",
        "checkpoint_conflict",
        "partial_collection_failure",
        "internal_collector_failure",
    }
)


def safe_error(code: str, retryable: bool = False) -> IntegrationError:
    if code not in ERROR_CODES:
        code = "internal_collector_failure"
    return IntegrationError(code, f"Azure collection failed: {code}", retryable=retryable)


def map_azure_error(exc: Exception) -> IntegrationError:
    status = getattr(exc, "status_code", None)
    if status in (401,):
        return safe_error("authentication_failed")
    if status in (403,):
        return safe_error("access_denied")
    if status in (404,):
        return safe_error("resource_not_found")
    if status == 429:
        return safe_error("rate_limited", True)
    if status in (408, 504):
        return safe_error("request_timeout", True)
    return safe_error("internal_collector_failure")
