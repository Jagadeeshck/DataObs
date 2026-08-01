from __future__ import annotations

from dataclasses import replace

from services.security.role_binding_repository import RoleBindingRepository
from src.config.settings import AuthSettings

from .errors import SecurityError
from .models import EffectiveAuthorization, Principal, TenantAccess
from .roles import permissions_for_roles


class AuthorizationResolver:
    """Converts a validated identity into context-scoped effective authority."""

    def __init__(self, settings: AuthSettings, repository: RoleBindingRepository | None):
        self.settings, self.repository = settings, repository

    def resolve(
        self, identity: Principal, tenant_id: str, environment: str | None
    ) -> tuple[Principal, EffectiveAuthorization]:
        mode = self.settings.authorization_source
        claim_access = any(
            a.tenant_id in {tenant_id, "*"} and (not environment or not a.environments or environment in a.environments)
            for a in identity.tenant_access
        )
        bindings = []
        if mode in {"bindings", "intersection"}:
            if self.repository is None:
                raise SecurityError(
                    "authorization_store_unavailable", "Authorization policy is unavailable", status_code=503
                )
            bindings = self.repository.find_effective_bindings(
                issuer=identity.issuer,
                subject=identity.subject,
                groups=set(identity.groups),
                client_id=identity.client_id,
                tenant_id=tenant_id,
                environment=environment,
            )
        if identity.is_service:
            bindings = [b for b in bindings if b.principal_type == "service" and b.principal_id == identity.client_id]
        if mode == "claims":
            roles, sources = identity.roles, {"claims"}
        else:
            binding_roles = frozenset(role for binding in bindings for role in binding.roles)
            if mode == "intersection" and not claim_access:
                binding_roles = frozenset()
            roles, sources = binding_roles, {"bindings"} | ({"claims"} if mode == "intersection" else set())
        if not roles:
            raise SecurityError("tenant_access_denied", "Tenant access is denied", status_code=403)
        permissions = permissions_for_roles(roles)
        effective = EffectiveAuthorization(
            tenant_id, environment, roles, permissions, frozenset(sources), frozenset(b.binding_id for b in bindings)
        )
        principal = replace(
            identity,
            roles=roles,
            permissions=permissions,
            tenant_access=frozenset(
                {TenantAccess(tenant_id, frozenset({environment}) if environment else frozenset())}
            ),
            active_tenant=tenant_id,
            active_environment=environment,
        )
        return principal, effective
