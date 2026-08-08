from packages.collectors.sdk.errors import IntegrationError


def safe_error(exc):
    text = str(exc)
    known = (
        "dependency_unavailable",
        "credential_unavailable",
        "credential_reference_invalid",
        "statement_timeout",
        "access_denied",
    )
    code = next((x for x in known if x in text), "coordinator_unavailable")
    error = IntegrationError("Trino collection unavailable")
    error.code = code
    error.retryable = code not in {"dependency_unavailable", "credential_reference_invalid"}
    return error
