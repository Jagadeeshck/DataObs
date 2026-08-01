from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .role_binding_repository import (
    ROLE_BINDING_ALIAS,
    RoleBinding,
    RoleBindingConflict,
    RoleBindingNotFound,
)


class ElasticsearchRoleBindingRepository:
    """OCC-backed repository using only the alias released by migration 0020."""

    def __init__(self, client, *, request_timeout: float = 10.0):
        self.client, self.request_timeout = client, request_timeout

    @staticmethod
    def _binding(source: dict) -> RoleBinding:
        source = dict(source)
        source["environments"] = tuple(source.get("environments", ()))
        source["roles"] = tuple(source.get("roles", ()))
        return RoleBinding(**source)

    def create(self, binding: RoleBinding) -> RoleBinding:
        try:
            self.client.create(
                index=ROLE_BINDING_ALIAS,
                id=binding.binding_id,
                document=binding.document(),
                refresh="wait_for",
                request_timeout=self.request_timeout,
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409:
                current = self.get(binding.binding_id)
                if current == binding:
                    return current
                raise RoleBindingConflict("binding already exists") from exc
            raise
        return binding

    def get(self, binding_id: str, tenant_id: str | None = None) -> RoleBinding:
        try:
            hit = self.client.get(index=ROLE_BINDING_ALIAS, id=binding_id, request_timeout=self.request_timeout)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                raise RoleBindingNotFound("role binding not found") from exc
            raise
        binding = self._binding(hit["_source"])
        if tenant_id is not None and binding.tenant_id != tenant_id:
            raise RoleBindingNotFound("role binding not found")
        return binding

    def list(self, tenant_id: str, *, limit: int = 100, cursor: str | None = None):
        size = max(1, min(limit, 200))
        body = {"size": size, "query": {"term": {"tenant_id": tenant_id}}, "sort": [{"binding_id": "asc"}]}
        if cursor:
            body["search_after"] = [cursor]
        result = self.client.search(index=ROLE_BINDING_ALIAS, **body, request_timeout=self.request_timeout)
        hits = result["hits"]["hits"]
        return [self._binding(h["_source"]) for h in hits], (hits[-1]["sort"][0] if len(hits) == size else None)

    def update(self, binding_id: str, tenant_id: str, changes: dict, if_match: str, actor: str) -> RoleBinding:
        current = self.get(binding_id, tenant_id)
        if not if_match or current.etag != if_match:
            raise RoleBindingConflict("role binding ETag mismatch")
        allowed = {"environments", "roles", "active", "description"}
        values = current.document() | {k: v for k, v in changes.items() if k in allowed}
        values["environments"] = tuple(sorted(set(values["environments"])))
        values["roles"] = tuple(sorted(set(values["roles"])))
        values["revision"] = current.revision + 1
        values["updated_at"] = datetime.now(timezone.utc).isoformat()
        values["updated_by"] = actor
        values["etag"] = hashlib.sha256(f"{binding_id}:{values['revision']}".encode()).hexdigest()
        updated = RoleBinding(**values)
        try:
            hit = self.client.get(index=ROLE_BINDING_ALIAS, id=binding_id, request_timeout=self.request_timeout)
            self.client.index(
                index=ROLE_BINDING_ALIAS,
                id=binding_id,
                document=updated.document(),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
                refresh="wait_for",
                request_timeout=self.request_timeout,
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409:
                raise RoleBindingConflict("concurrent role binding update") from exc
            raise
        return updated

    def disable(self, binding_id: str, tenant_id: str, if_match: str, actor: str) -> RoleBinding:
        return self.update(binding_id, tenant_id, {"active": False}, if_match, actor)

    def find_effective_bindings(
        self, issuer: str, subject: str, groups: set[str], tenant_id: str, environment: str | None
    ):
        should = [{"bool": {"must": [{"term": {"principal_type": "user"}}, {"term": {"principal_id": subject}}]}}]
        if groups:
            should.append(
                {"bool": {"must": [{"term": {"principal_type": "group"}}, {"terms": {"principal_id": sorted(groups)}}]}}
            )
        query = {
            "bool": {
                "filter": [
                    {"term": {"issuer": issuer}},
                    {"term": {"tenant_id": tenant_id}},
                    {"term": {"active": True}},
                ],
                "should": should,
                "minimum_should_match": 1,
            }
        }
        hits = self.client.search(
            index=ROLE_BINDING_ALIAS,
            query=query,
            size=200,
            sort=[{"binding_id": "asc"}],
            request_timeout=self.request_timeout,
        )["hits"]["hits"]
        bindings = [self._binding(h["_source"]) for h in hits]
        return [b for b in bindings if not environment or not b.environments or environment in b.environments]

    def count_active_platform_administrators(self) -> int:
        query = {"bool": {"filter": [{"term": {"active": True}}, {"term": {"roles": "platform_admin"}}]}}
        return int(
            self.client.count(index=ROLE_BINDING_ALIAS, query=query, request_timeout=self.request_timeout)["count"]
        )
