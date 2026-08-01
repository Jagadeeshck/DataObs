from __future__ import annotations

from typing import Any

from .role_binding_repository import (
    LastAdministratorError,
    RoleBinding,
    RoleBindingConflict,
    RoleBindingNotFound,
)

# Exact mutable index alias released by migration 0020. Callers cannot override it.
ROLE_BINDING_ALIAS = "dataobs-role-bindings-v1"


class ElasticsearchRoleBindingRepository:
    def __init__(self, client: Any, *, request_timeout: float = 10.0, max_page_size: int = 200):
        self.client, self.request_timeout, self.max_page_size = client, request_timeout, max_page_size

    @staticmethod
    def _binding(source: dict) -> RoleBinding:
        return RoleBinding(**{**source, "environments": tuple(source["environments"]), "roles": tuple(source["roles"])})

    def create(self, binding: RoleBinding) -> RoleBinding:
        try:
            self.client.create(
                index=ROLE_BINDING_ALIAS,
                id=binding.binding_id,
                document=binding.document(),
                refresh="wait_for",
                request_timeout=self.request_timeout,
            )
            return binding
        except Exception as exc:
            if getattr(exc, "status_code", None) != 409 and getattr(exc, "meta", None) is None:
                raise
            existing = self.get(binding.binding_id)
            if existing.document() == binding.document():
                return existing
            raise RoleBindingConflict("binding already exists") from exc

    def get(self, binding_id: str, tenant_id: str | None = None) -> RoleBinding:
        try:
            result = self.client.get(index=ROLE_BINDING_ALIAS, id=binding_id, request_timeout=self.request_timeout)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                raise RoleBindingNotFound("role binding not found") from exc
            raise
        binding = self._binding(result["_source"])
        if tenant_id is not None and binding.tenant_id != tenant_id:
            raise RoleBindingNotFound("role binding not found")
        return binding

    def list(self, tenant_id: str, *, limit: int = 100, after: str | None = None):
        size = max(1, min(limit, self.max_page_size))
        body = {
            "size": size + 1,
            "query": {"term": {"tenant_id": tenant_id}},
            "sort": [{"binding_id": "asc"}],
            "_source": True,
        }
        if after:
            body["search_after"] = [after]
        result = self.client.search(index=ROLE_BINDING_ALIAS, body=body, request_timeout=self.request_timeout)
        values = [self._binding(hit["_source"]) for hit in result["hits"]["hits"]]
        return values[:size], (values[size - 1].binding_id if len(values) > size else None)

    def update(self, binding_id: str, tenant_id: str, *, if_match: str, actor: str, **changes) -> RoleBinding:
        current = self.get(binding_id, tenant_id)
        if not if_match or current.etag != if_match:
            raise RoleBindingConflict("role binding ETag mismatch")
        updated = current.changed(actor=actor, **changes)
        # ETag is checked again atomically in the update script, so concurrent writers cannot both succeed.
        script = {
            "lang": "painless",
            "source": "if (ctx._source.etag != params.expected) { ctx.op='none'; } else { ctx._source=params.doc; }",
            "params": {"expected": if_match, "doc": updated.document()},
        }
        result = self.client.update(
            index=ROLE_BINDING_ALIAS,
            id=binding_id,
            script=script,
            refresh="wait_for",
            request_timeout=self.request_timeout,
        )
        if result.get("result") == "noop":
            raise RoleBindingConflict("concurrent role binding update")
        return updated

    def disable(self, binding_id: str, tenant_id: str, *, if_match: str, actor: str) -> RoleBinding:
        current = self.get(binding_id, tenant_id)
        if current.active and "platform_admin" in current.roles and self.count_active_platform_administrators() <= 1:
            raise LastAdministratorError("cannot disable the final platform administrator")
        return self.update(binding_id, tenant_id, if_match=if_match, actor=actor, active=False)

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
        identities = [{"bool": {"must": [{"term": {"principal_type": "user"}}, {"term": {"principal_id": subject}}]}}]
        identities += [
            {"bool": {"must": [{"term": {"principal_type": "group"}}, {"term": {"principal_id": g}}]}}
            for g in sorted(groups)
        ]
        if client_id:
            identities.append(
                {"bool": {"must": [{"term": {"principal_type": "service"}}, {"term": {"principal_id": client_id}}]}}
            )
        filters: list[dict] = [
            {"term": {"issuer": issuer}},
            {"term": {"active": True}},
            {"bool": {"should": identities, "minimum_should_match": 1}},
        ]
        if tenant_id:
            filters.append({"term": {"tenant_id": tenant_id}})
        if environment:
            filters.append({"term": {"environments": environment}})
        result = self.client.search(
            index=ROLE_BINDING_ALIAS,
            size=self.max_page_size,
            query={"bool": {"filter": filters}},
            sort=[{"binding_id": "asc"}],
            request_timeout=self.request_timeout,
        )
        return [self._binding(hit["_source"]) for hit in result["hits"]["hits"]]

    def count_active_platform_administrators(self) -> int:
        result = self.client.count(
            index=ROLE_BINDING_ALIAS,
            query={"bool": {"filter": [{"term": {"active": True}}, {"term": {"roles": "platform_admin"}}]}},
            request_timeout=self.request_timeout,
        )
        return int(result["count"])
