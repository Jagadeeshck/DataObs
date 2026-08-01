"""Stable, persistence-safe integration error taxonomy."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_CONFIGURATION = "invalid_configuration"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    RESOURCE_NOT_FOUND = "resource_not_found"
    THROTTLED = "provider_throttled"
    TRANSIENT_FAILURE = "transient_provider_failure"
    TIMEOUT = "collection_timeout"
    CANCELLED = "collection_cancelled"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    MALFORMED_RESPONSE = "malformed_provider_response"
    CHECKPOINT_CONFLICT = "checkpoint_conflict"
    PARTIAL_FAILURE = "partial_collection_failure"
    INTERNAL = "internal_collector_error"


class IntegrationError(Exception):
    """An error safe to classify across provider boundaries."""

    code = ErrorCode.INTERNAL
    retryable = False

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _error(name: str, code: ErrorCode, retryable: bool = False) -> type[IntegrationError]:
    return type(name, (IntegrationError,), {"code": code, "retryable": retryable})


InvalidConfigurationError = _error("InvalidConfigurationError", ErrorCode.INVALID_CONFIGURATION)
AuthenticationError = _error("AuthenticationError", ErrorCode.AUTHENTICATION_FAILED)
AuthorizationError = _error("AuthorizationError", ErrorCode.AUTHORIZATION_FAILED)
DependencyUnavailableError = _error("DependencyUnavailableError", ErrorCode.DEPENDENCY_UNAVAILABLE, True)
ResourceNotFoundError = _error("ResourceNotFoundError", ErrorCode.RESOURCE_NOT_FOUND)
ProviderThrottledError = _error("ProviderThrottledError", ErrorCode.THROTTLED, True)
TransientProviderError = _error("TransientProviderError", ErrorCode.TRANSIENT_FAILURE, True)
CollectionTimeoutError = _error("CollectionTimeoutError", ErrorCode.TIMEOUT, True)
CollectionCancelledError = _error("CollectionCancelledError", ErrorCode.CANCELLED)
UnsupportedCapabilityError = _error("UnsupportedCapabilityError", ErrorCode.UNSUPPORTED_CAPABILITY)
MalformedProviderResponseError = _error("MalformedProviderResponseError", ErrorCode.MALFORMED_RESPONSE)
CheckpointConflictError = _error("CheckpointConflictError", ErrorCode.CHECKPOINT_CONFLICT, True)
PartialCollectionError = _error("PartialCollectionError", ErrorCode.PARTIAL_FAILURE)
InternalCollectorError = _error("InternalCollectorError", ErrorCode.INTERNAL)
