from __future__ import annotations

from packages.collectors.sdk.errors import IntegrationError

CODES = frozenset(
    "invalid_configuration dependency_unavailable credential_reference_invalid credential_unavailable credential_format_invalid authentication_failed token_expired impersonation_denied principal_mismatch project_mismatch project_unavailable location_mismatch access_denied resource_not_found quota_exceeded rate_limited request_timeout query_timeout query_cancelled maximum_bytes_exceeded result_truncated result_malformed pagination_token_invalid pagination_token_loop unsupported_feature checkpoint_conflict partial_collection_failure internal_collector_failure".split()
)


def safe_error(code: str, message: str | None = None, retryable: bool = False) -> IntegrationError:
    code = code if code in CODES else "internal_collector_failure"
    return IntegrationError(code, message or code.replace("_", " "), retryable=retryable)


def map_google_error(exc: Exception) -> IntegrationError:
    name = type(exc).__name__.lower()
    if "permission" in name or "forbidden" in name:
        return safe_error("access_denied")
    if "quota" in name:
        return safe_error("quota_exceeded", retryable=True)
    if "timeout" in name or "deadline" in name:
        return safe_error("request_timeout", retryable=True)
    if "notfound" in name:
        return safe_error("resource_not_found")
    return safe_error("internal_collector_failure")
