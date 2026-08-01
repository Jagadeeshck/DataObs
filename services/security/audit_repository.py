from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Protocol

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
class AuditEvent:
    event_action: str
    event_outcome: str
    reason_code: str
    request_id: str
    event_category: str = "authentication"
    timestamp: str = ""
    trace_id: str | None = None
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

    def document(self) -> dict:
        value = {k: v for k, v in asdict(self).items() if v is not None}
        value["@timestamp"] = value.pop("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return value


class AuditRepository(Protocol):
    def append(self, event: AuditEvent) -> None: ...
