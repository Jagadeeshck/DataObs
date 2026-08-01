from packages.collectors.sdk.errors import (
    AuthenticationError,
    AuthorizationError,
    DependencyUnavailableError,
    ProviderThrottledError,
)


def map_aws_error(exc: Exception):
    code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
        return AuthorizationError("AWS operation is not permitted")
    if code in {"ExpiredToken", "InvalidClientTokenId", "UnrecognizedClientException"}:
        return AuthenticationError("AWS credentials are invalid or expired")
    if code in {"Throttling", "ThrottlingException", "TooManyRequestsException"}:
        return ProviderThrottledError("AWS request was throttled")
    return DependencyUnavailableError("AWS dependency is unavailable or returned a malformed response")
