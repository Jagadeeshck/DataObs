from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

ROLE_BINDING_ALIAS = "dataobs-role-bindings-v1"
PRINCIPAL_TYPES = frozenset({"user", "group", "service"})


class RoleBindingError(RuntimeError):
    pass


class RoleBindingNotFound(RoleBindingError):
    pass


class RoleBindingConflict(RoleBindingError):
    pass


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
        environments: tuple[str, ...],
        roles: tuple[str, ...],
        description: str,
        actor: str,
    ) -> "RoleBinding":
        if principal_type not in PRINCIPAL_TYPES:
            raise ValueError("unsupported principal type")
        binding_id = hashlib.sha256(f"{issuer}\0{principal_type}\0{principal_id}\0{tenant_id}".encode()).hexdigest()[
            :32
        ]
        now = datetime.now(timezone.utc).isoformat()
        etag = hashlib.sha256(f"{binding_id}:1".encode()).hexdigest()
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
            etag,
        )

    def document(self) -> dict:
        return dict(self.__dict__)


class RoleBindingRepository(Protocol):
    def create(self, binding: RoleBinding) -> RoleBinding: ...
    def get(self, binding_id: str, tenant_id: str | None = None) -> RoleBinding: ...
    def list(
        self, tenant_id: str, *, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[RoleBinding], str | None]: ...
    def update(self, binding_id: str, tenant_id: str, changes: dict, if_match: str, actor: str) -> RoleBinding: ...
    def disable(self, binding_id: str, tenant_id: str, if_match: str, actor: str) -> RoleBinding: ...
    def find_effective_bindings(
        self, issuer: str, subject: str, groups: set[str], tenant_id: str, environment: str | None
    ) -> list[RoleBinding]: ...
    def count_active_platform_administrators(self) -> int: ...
