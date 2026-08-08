from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Protocol

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from .contracts import CaseLink


class CaseLinkConflict(RuntimeError):
    pass


class CaseLinkRepository(Protocol):
    def get_for_incident(self, tenant_id: str, environment: str, incident_id: str, space: str) -> CaseLink | None: ...
    def reserve(self, link: CaseLink) -> CaseLink: ...
    def update(self, link: CaseLink, expected_revision: int) -> CaseLink: ...


class InMemoryCaseLinkRepository:
    def __init__(self) -> None:
        self._items: dict[str, CaseLink] = {}
        self._lock = Lock()

    def get_for_incident(self, tenant_id: str, environment: str, incident_id: str, space: str) -> CaseLink | None:
        item = self._items.get(f"{tenant_id}:{environment}:{incident_id}:{space}")
        return deepcopy(item)

    def reserve(self, link: CaseLink) -> CaseLink:
        key = f"{link.tenant_id}:{link.environment}:{link.incident_id}:{link.kibana_space}"
        with self._lock:
            existing = self._items.setdefault(key, link.model_copy(deep=True))
            if existing.reconciliation_reference != link.reconciliation_reference:
                raise CaseLinkConflict("case reservation identity conflict")
            return existing.model_copy(deep=True)

    def update(self, link: CaseLink, expected_revision: int) -> CaseLink:
        key = f"{link.tenant_id}:{link.environment}:{link.incident_id}:{link.kibana_space}"
        with self._lock:
            current = self._items.get(key)
            if not current or current.revision != expected_revision:
                raise CaseLinkConflict("case link revision conflict")
            link.revision += 1
            self._items[key] = link.model_copy(deep=True)
            return link.model_copy(deep=True)


CASE_LINK_READ = "dataobs-case-links-v1-read"
CASE_LINK_WRITE = "dataobs-case-links-v1-write"


def _document(link: CaseLink) -> dict[str, object]:
    return {
        "tenant_id": link.tenant_id,
        "environment": link.environment,
        "incident_id": link.incident_id,
        "case_link_id": link.link_id,
        "case_id": link.elastic_case_id,
        "kibana_space": link.kibana_space,
        "status": link.state.value,
        "updated_at": (link.last_attempted_sync or link.last_successful_sync),
        "metadata": link.model_dump(mode="json"),
    }


class ElasticsearchCaseRepository:
    """Strict-envelope Case link adapter with create reservation and Elasticsearch OCC."""

    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    def _get(self, link_id: str, tenant_id: str, environment: str, space: str) -> tuple[CaseLink, int, int] | None:
        try:
            hit = self.client.get(index=CASE_LINK_READ, id=link_id)
        except NotFoundError:
            return None
        source = hit["_source"]
        if (source.get("tenant_id"), source.get("environment"), source.get("kibana_space")) != (
            tenant_id,
            environment,
            space,
        ):
            return None
        return CaseLink.model_validate(source["metadata"]), int(hit["_seq_no"]), int(hit["_primary_term"])

    def reserve_create(self, link: CaseLink) -> CaseLink:
        try:
            self.client.create(index=CASE_LINK_WRITE, id=link.link_id, document=_document(link), refresh="wait_for")
            return link
        except ConflictError:
            current = self._get(link.link_id, link.tenant_id, link.environment, link.kibana_space)
            if not current or current[0].reconciliation_reference != link.reconciliation_reference:
                raise CaseLinkConflict("case reservation identity conflict")
            return current[0]

    reserve = reserve_create

    def get_by_link_id(self, tenant_id: str, environment: str, space: str, link_id: str) -> CaseLink | None:
        result = self._get(link_id, tenant_id, environment, space)
        return result[0] if result else None

    def _search(
        self, tenant_id: str, environment: str, space: str, filters: list[dict[str, object]], *, size: int = 25
    ) -> list[CaseLink]:
        response = self.client.search(
            index=CASE_LINK_READ,
            size=min(max(size, 1), 100),
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"kibana_space": space}},
                        *filters,
                    ]
                }
            },
            sort=[{"updated_at": "asc"}, {"case_link_id": "asc"}],
        )
        return [CaseLink.model_validate(hit["_source"]["metadata"]) for hit in response["hits"]["hits"]]

    def get_by_incident(self, tenant_id: str, environment: str, incident_id: str, space: str) -> CaseLink | None:
        items = self._search(tenant_id, environment, space, [{"term": {"incident_id": incident_id}}], size=1)
        return items[0] if items else None

    get_for_incident = get_by_incident

    def get_by_case_id(self, tenant_id: str, environment: str, space: str, case_id: str) -> CaseLink | None:
        items = self._search(tenant_id, environment, space, [{"term": {"case_id": case_id}}], size=1)
        return items[0] if items else None

    def update_link_occ(self, link: CaseLink, expected_revision: int) -> CaseLink:
        current = self._get(link.link_id, link.tenant_id, link.environment, link.kibana_space)
        if not current or current[0].revision != expected_revision:
            raise CaseLinkConflict("case link revision conflict")
        link.revision = expected_revision + 1
        try:
            self.client.index(
                index=CASE_LINK_WRITE,
                id=link.link_id,
                document=_document(link),
                if_seq_no=current[1],
                if_primary_term=current[2],
                refresh="wait_for",
            )
        except ConflictError as exc:
            raise CaseLinkConflict("case link revision conflict") from exc
        return link

    update = update_link_occ

    def _mark(self, link: CaseLink, state: str, **changes: object) -> CaseLink:
        expected = link.revision
        updated = link.model_copy(update={"state": state, **changes})
        return self.update_link_occ(updated, expected)

    def mark_submitted(self, link: CaseLink) -> CaseLink:
        return self._mark(link, "create_submitted")

    def mark_linked(self, link: CaseLink, case_id: str, version: str | None = None) -> CaseLink:
        return self._mark(link, "linked", elastic_case_id=case_id[:256], elastic_case_version=version)

    def mark_reconciliation_required(self, link: CaseLink) -> CaseLink:
        return self._mark(link, "create_reconciliation_required")

    def mark_sync_result(self, link: CaseLink, sync_state: str) -> CaseLink:
        return self._mark(link, link.state.value, sync_state=sync_state[:32])

    def list_reconciliation_due(self, tenant_id: str, environment: str, space: str, limit: int = 25) -> list[CaseLink]:
        return self._search(
            tenant_id, environment, space, [{"term": {"status": "create_reconciliation_required"}}], size=limit
        )

    def search_links(self, tenant_id: str, environment: str, space: str, limit: int = 25) -> list[CaseLink]:
        return self._search(tenant_id, environment, space, [], size=limit)
