"""Development/test-only role-binding repository."""

from __future__ import annotations

from threading import RLock

from .role_binding_repository import LastAdministratorError, RoleBinding, RoleBindingConflict, RoleBindingNotFound


class InMemoryRoleBindingRepository:
    def __init__(self) -> None:
        self._bindings: dict[str, RoleBinding] = {}
        self._lock = RLock()

    def create(self, binding: RoleBinding) -> RoleBinding:
        with self._lock:
            existing = self._bindings.get(binding.binding_id)
            if existing:
                comparable = (
                    "issuer",
                    "principal_type",
                    "principal_id",
                    "tenant_id",
                    "environments",
                    "roles",
                    "description",
                )
                if all(getattr(existing, field) == getattr(binding, field) for field in comparable):
                    return existing
                raise RoleBindingConflict("binding already exists with different content")
            self._bindings[binding.binding_id] = binding
            return binding

    def get(self, binding_id: str, tenant_id: str | None = None) -> RoleBinding:
        with self._lock:
            value = self._bindings.get(binding_id)
            if value is None or (tenant_id is not None and value.tenant_id != tenant_id):
                raise RoleBindingNotFound("role binding not found")
            return value

    def list(self, tenant_id: str, *, limit: int = 100, after: str | None = None):
        with self._lock:
            values = sorted(
                (v for v in self._bindings.values() if v.tenant_id == tenant_id), key=lambda v: v.binding_id
            )
            if after:
                values = [v for v in values if v.binding_id > after]
            size = max(1, min(limit, 200))
            return values[:size], (values[size - 1].binding_id if len(values) > size else None)

    def update(self, binding_id: str, tenant_id: str, *, if_match: str, actor: str, **changes) -> RoleBinding:
        with self._lock:
            current = self.get(binding_id, tenant_id)
            if current.etag != if_match:
                raise RoleBindingConflict("role binding ETag mismatch")
            updated = current.changed(actor=actor, **changes)
            self._bindings[binding_id] = updated
            return updated

    def disable(self, binding_id: str, tenant_id: str, *, if_match: str, actor: str) -> RoleBinding:
        with self._lock:
            current = self.get(binding_id, tenant_id)
            if current.etag != if_match:
                raise RoleBindingConflict("role binding ETag mismatch")
            if (
                current.active
                and "platform_admin" in current.roles
                and self.count_active_platform_administrators() <= 1
            ):
                raise LastAdministratorError("cannot disable the final platform administrator")
            return self.update(binding_id, tenant_id, if_match=if_match, actor=actor, active=False)

    def count_active_platform_administrators(self) -> int:
        with self._lock:
            return sum(v.active and "platform_admin" in v.roles for v in self._bindings.values())

    def find_effective_bindings(
        self,
        *,
        issuer: str,
        subject: str,
        groups: set[str],
        client_id: str | None,
        tenant_id: str | None = None,
        environment: str | None = None,
    ):
        identities = {("user", subject), *(("group", group) for group in groups)}
        if client_id:
            identities.add(("service", client_id))
        with self._lock:
            return [
                v
                for v in self._bindings.values()
                if v.active
                and v.issuer == issuer
                and (v.principal_type, v.principal_id) in identities
                and (tenant_id is None or v.tenant_id == tenant_id)
                and (environment is None or environment in v.environments)
            ]
