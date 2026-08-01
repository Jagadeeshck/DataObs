from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

SECURITY_EVENT_DATA_STREAM = "logs-dataobs.security-event-default"
SECURITY_ACTIONS = frozenset(
    {
        "authentication_failed",
        "permission_denied",
        "tenant_access_denied",
        "environment_access_denied",
        "role_binding_created",
        "role_binding_updated",
        "role_binding_disabled",
        "role_escalation_denied",
        "last_administrator_protection_triggered",
        "security_configuration_rejected",
        "service_principal_denied",
        "OIDC_key_refresh_failed",
    }
)


@dataclass(frozen=True)
class SecurityAuditEvent:
    timestamp: str
    event_action: str
    event_category: str
    event_outcome: str
    reason_code: str
    request_id: str
    principal_subject: str | None = None
    principal_type: str | None = None
    issuer: str | None = None
    tenant_id: str | None = None
    environment: str | None = None
    binding_id: str | None = None
    route: str | None = None
    http_method: str | None = None
    source_ip_hash: str | None = None
    user_agent_hash: str | None = None
    schema_version: str = "v1"


class AuditRepository(Protocol):
    def append(self, event: SecurityAuditEvent) -> None: ...
