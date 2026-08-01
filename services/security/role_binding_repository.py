from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Protocol

PRINCIPAL_TYPES = frozenset({"user", "group", "service"})

ROLE_BINDING_ALIAS = "dataobs-role-bindings-v1"


class RoleBindingError(Exception):
    """Base error safe for translation to an API error."""


class RoleBindingNotFound(RoleBindingError):
    pass


class RoleBindingConflict(RoleBindingError):
    pass


class LastAdministratorError(RoleBindingConflict):
    pass


def deterministic_binding_id(issuer: str, principal_type: str, principal_id: str, tenant_id: str) -> str:
    value = "\0".join((issuer, principal_type, principal_id, tenant_id)).encode()
    return hashlib.sha256(value).hexdigest()[:32]


def binding_etag(binding_id: str, revision: int) -> str:
    return '"' + hashlib.sha256(f"{binding_id}:{revision}".encode()).hexdigest() + '"'


@dataclass(frozen=True)
class RoleBinding:
    binding_id: str
    issuer: str
    principal_type: str
    principal_id: str
    tenant_id: str
    environments: tuple[str, ...]
    roles: tuple[str, ...]
    active: bool
    description: str
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str
    revision: int
    etag: str
    schema_version: str = "v1"

    @classmethod
    def new(
        cls,
        *,
        issuer: str,
        principal_type: str,
        principal_id: str,
        tenant_id: str,
        environments: list[str] | tuple[str, ...],
        roles: list[str] | tuple[str, ...],
        description: str = "",
        actor: str,
    ) -> "RoleBinding":
        if principal_type not in PRINCIPAL_TYPES:
            raise ValueError("unsupported principal type")
        binding_id = deterministic_binding_id(issuer, principal_type, principal_id, tenant_id)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return cls(
            binding_id,
            issuer,
            principal_type,
            principal_id,
            tenant_id,
            tuple(sorted(set(environments))),
            tuple(sorted(set(roles))),
            True,
            description,
            now,
            actor,
            now,
            actor,
            1,
            binding_etag(binding_id, 1),
        )

    def document(self) -> dict:
        value = asdict(self)
        value["environments"] = list(self.environments)
        value["roles"] = list(self.roles)
        return value

    def changed(self, *, environments=None, roles=None, active=None, description=None, actor: str) -> "RoleBinding":
        revision = self.revision + 1
        return replace(
            self,
            environments=self.environments if environments is None else tuple(sorted(set(environments))),
            roles=self.roles if roles is None else tuple(sorted(set(roles))),
            active=self.active if active is None else active,
            description=self.description if description is None else description,
            updated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            updated_by=actor,
            revision=revision,
            etag=binding_etag(self.binding_id, revision),
        )


class RoleBindingRepository(Protocol):
    def create(self, binding: RoleBinding) -> RoleBinding: ...
    def get(self, binding_id: str, tenant_id: str | None = None) -> RoleBinding: ...
    def list(
        self, tenant_id: str, *, limit: int = 100, after: str | None = None
    ) -> tuple[list[RoleBinding], str | None]: ...
    def update(self, binding_id: str, tenant_id: str, *, if_match: str, actor: str, **changes) -> RoleBinding: ...
    def disable(self, binding_id: str, tenant_id: str, *, if_match: str, actor: str) -> RoleBinding: ...
    def find_effective_bindings(
        self,
        *,
        issuer: str,
        subject: str,
        groups: set[str],
        client_id: str | None,
        tenant_id: str | None = None,
        environment: str | None = None,
    ) -> list[RoleBinding]: ...
    def count_active_platform_administrators(self) -> int: ...
