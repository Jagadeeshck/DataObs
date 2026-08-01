from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.config.settings import AuthSettings

from .errors import SecurityError
from .models import Principal, TenantAccess
from .oidc import OIDCValidator
from .roles import permissions_for_roles


def _strings(value: Any, claim: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SecurityError("mandatory_claim_malformed", f"Configured {claim} claim is malformed")
    return frozenset(value)


def principal_from_claims(claims: dict[str, Any], settings: AuthSettings) -> Principal:
    oidc = settings.oidc
    groups = _strings(claims.get(oidc.groups_claim), oidc.groups_claim)
    roles = {role for group in groups for role in oidc.group_role_mappings.get(group, ())}
    if groups.intersection(oidc.platform_admin_groups):
        roles.add("platform_admin")
    access_claim = claims.get(oidc.tenants_claim, [])
    if not isinstance(access_claim, list):
        raise SecurityError("mandatory_claim_malformed", "Configured tenant claim is malformed")
    access: set[TenantAccess] = set()
    for entry in access_claim:
        if isinstance(entry, str):
            access.add(TenantAccess(entry, frozenset()))
        elif isinstance(entry, dict) and isinstance(entry.get("tenant_id"), str):
            access.add(TenantAccess(entry["tenant_id"], _strings(entry.get("environments", []), "environments")))
        else:
            raise SecurityError("mandatory_claim_malformed", "Configured tenant claim is malformed")
    subject = claims.get(oidc.subject_claim)
    if not isinstance(subject, str) or not subject:
        raise SecurityError("mandatory_claim_missing", "Access token subject is missing")
    client_id = claims.get("client_id") or claims.get("azp")
    principal_type = "service" if isinstance(client_id, str) and client_id in oidc.allowed_service_clients else "user"
    if principal_type == "service" and oidc.require_jti_for_service_tokens and not claims.get("jti"):
        raise SecurityError("service_principal_denied", "Service access token requires a token identifier")
    if principal_type == "service":
        # Service identities never inherit browser group/bootstrap authority.
        roles = set()
    return Principal(
        subject=subject,
        issuer=str(claims.get("iss", oidc.issuer)),
        principal_type=principal_type,
        display_name=claims.get("name") if isinstance(claims.get("name"), str) else None,
        username=claims.get(oidc.username_claim) if isinstance(claims.get(oidc.username_claim), str) else None,
        groups=groups,
        token_id=claims.get("jti") if isinstance(claims.get("jti"), str) else None,
        authentication_time=_date(claims.get("auth_time")),
        expires_at=_date(claims.get("exp")),
        roles=frozenset(roles),
        permissions=permissions_for_roles(frozenset(roles)),
        tenant_access=frozenset(access),
        is_service=principal_type == "service",
    )


def _date(value: Any) -> datetime | None:
    return datetime.fromtimestamp(value, timezone.utc) if isinstance(value, (int, float)) else None


class Authenticator:
    def __init__(self, settings: AuthSettings):
        self.settings = settings
        self.validator = OIDCValidator(settings.oidc) if settings.provider == "oidc" else None

    def authenticate(self, token: str | None) -> Principal:
        if self.settings.provider == "oidc":
            if not token:
                raise SecurityError("token_missing", "Bearer access token is required")
            return principal_from_claims(self.validator.validate(token), self.settings)  # type: ignore[union-attr]
        if self.settings.provider in {"token", "local"} and token and token == self.settings.api_token:
            return self._development_principal()
        if self.settings.provider == "local" and self.settings.allow_unauthenticated_dev:
            return self._development_principal()
        raise SecurityError("token_missing" if not token else "signature_invalid", "Valid authentication is required")

    @staticmethod
    def _development_principal() -> Principal:
        roles = frozenset({"platform_admin"})
        return Principal(
            "local-development",
            "dataobs:local",
            "user",
            roles=roles,
            permissions=permissions_for_roles(roles),
            tenant_access=frozenset({TenantAccess("default", frozenset()), TenantAccess("*", frozenset())}),
        )
