from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .capabilities import Capability
from .errors import InvalidConfigurationError


class CredentialReferenceType(StrEnum):
    ENVIRONMENT = "environment"
    KUBERNETES_SECRET = "kubernetes_secret"
    CLOUD_SECRET_MANAGER = "cloud_secret_manager"
    EXTERNAL_SECRET = "external_secret"


@dataclass(frozen=True)
class CredentialReference:
    kind: CredentialReferenceType
    reference: str

    def __post_init__(self) -> None:
        if not self.reference or "\n" in self.reference:
            raise InvalidConfigurationError("credential reference must be non-empty and single-line")

    def __repr__(self) -> str:
        return f"CredentialReference(kind={self.kind!r}, reference='[REDACTED]')"


@dataclass(frozen=True)
class IntegrationConfiguration:
    schema_version: str
    integration_id: str
    provider_type: str
    enabled: bool
    timeout_seconds: float
    allowed_capabilities: frozenset[Capability]
    credential: CredentialReference | None = None
    schedule: str | None = None
    resource_filters: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    rate_limit_per_second: float = 1.0
    checkpoint_enabled: bool = True
    provider: Mapping[str, Any] = field(default_factory=dict)
    redaction: Mapping[str, Any] = field(default_factory=dict)
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != "v1":
            raise InvalidConfigurationError("only integration configuration schema v1 is supported")
        if not self.integration_id or not self.provider_type:
            raise InvalidConfigurationError("integration_id and provider_type are required")
        if not 0 < self.timeout_seconds <= 3600:
            raise InvalidConfigurationError("timeout_seconds must be in (0, 3600]")
        if not 0 < self.rate_limit_per_second <= 100:
            raise InvalidConfigurationError("rate_limit_per_second must be in (0, 100]")
        forbidden = {"tenant_id", "tenant", "access_key", "secret_key", "password", "token"}
        if forbidden & {key.lower() for key in self.provider}:
            raise InvalidConfigurationError("provider configuration contains a trusted or secret field")
