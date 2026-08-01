from __future__ import annotations

from packages.collectors.sdk.errors import IntegrationError

ERROR_CODES = frozenset(
    {
        "invalid_configuration",
        "dependency_unavailable",
        "credential_reference_invalid",
        "credential_unavailable",
        "authentication_failed",
        "token_expired",
        "workspace_mismatch",
        "workspace_unavailable",
        "access_denied",
        "resource_not_found",
        "rate_limited",
        "request_timeout",
        "statement_timeout",
        "statement_cancelled",
        "statement_failed",
        "result_truncated",
        "result_malformed",
        "pagination_token_invalid",
        "pagination_token_loop",
        "unsupported_feature",
        "checkpoint_conflict",
        "partial_collection_failure",
        "internal_collector_failure",
    }
)


def safe_error(code: str, *, retryable: bool = False) -> IntegrationError:
    if code not in ERROR_CODES:
        code = "internal_collector_failure"
    error = IntegrationError(f"Databricks collection failed ({code})")
    error.code = code  # type: ignore[assignment]
    error.retryable = retryable  # type: ignore[assignment]
    return error


def map_sdk_error(exc: Exception) -> IntegrationError:
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = None
    status_codes = {
        401: "authentication_failed",
        403: "access_denied",
        404: "resource_not_found",
        429: "rate_limited",
    }
    code = status_codes.get(status) if status is not None else None
    if code is None:
        code = "request_timeout" if isinstance(exc, TimeoutError) else "workspace_unavailable"
    return safe_error(code, retryable=code in {"rate_limited", "request_timeout", "workspace_unavailable"})
