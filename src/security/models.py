from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .permissions import Permission


@dataclass(frozen=True, order=True)
class TenantAccess:
    tenant_id: str
    environments: frozenset[str]


@dataclass(frozen=True)
class Principal:
    subject: str
    issuer: str
    principal_type: str
    display_name: str | None = None
    username: str | None = None
    groups: frozenset[str] = frozenset()
    token_id: str | None = None
    authentication_time: datetime | None = None
    expires_at: datetime | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[Permission] = frozenset()
    tenant_access: frozenset[TenantAccess] = frozenset()
    active_tenant: str | None = None
    active_environment: str | None = None
    is_service: bool = False

    @property
    def authorised_tenants(self) -> frozenset[str]:
        return frozenset(access.tenant_id for access in self.tenant_access)

    def with_context(self, tenant: str, environment: str | None) -> Principal:
        return replace(self, active_tenant=tenant, active_environment=environment)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    environment: str | None
    principal_subject: str
    request_id: str
    trace_id: str | None = None
    authorisation_source: str = "validated_identity"
