from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Protocol


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RepositoryError(RuntimeError):
    pass


class NotFoundError(RepositoryError):
    pass


class ConflictError(RepositoryError):
    pass


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_memberships: tuple[str, ...]
    scopes: tuple[str, ...]
    auth_method: str
    service_identity: str | None = None

    def can_access(self, tenant_id: str) -> bool:
        return tenant_id in self.tenant_memberships or "*" in self.tenant_memberships


SCOPES = {
    "tenant_admin": "dataobs:tenant:admin",
    "source_admin": "dataobs:source:admin",
    "scanner_registration": "dataobs:scanner:register",
    "task_polling": "dataobs:task:poll",
    "result_submission": "dataobs:result:submit",
    "policy_admin": "dataobs:policy:admin",
    "asset_read": "dataobs:asset:read",
}


class CollectionRepository(Protocol):
    def upsert(self, bucket: str, doc: Dict[str, Any], *, expected_version: int | None = None) -> Dict[str, Any]: ...
    def get(self, bucket: str, id: str, tenant_id: str | None = None) -> Dict[str, Any] | None: ...
    def list(self, bucket: str, tenant_id: str, **filters: Any) -> List[Dict[str, Any]]: ...
    def delete(self, bucket: str, id: str, tenant_id: str, *, expected_version: int | None = None) -> None: ...
    def event(self, event_type: str, doc: Dict[str, Any]) -> Dict[str, Any]: ...
    def audit_event(
        self, action: str, tenant_id: str, correlation_id: str | None, resource_id: str
    ) -> Dict[str, Any]: ...
    def readiness(self) -> Dict[str, Any]: ...
