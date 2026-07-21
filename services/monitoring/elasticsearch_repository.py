"""Elasticsearch-backed monitor repository.

All resource names are compile-time constants. IDs include a hash of tenant and
environment so identical business IDs cannot collide across scopes.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from packages.domain_model.monitor import MonitorDefinition
from services.monitoring.repository import VersionConflict

MONITORS_ALIAS = "dataobs-monitor-definitions-v2"
DEFINITION_HISTORY_ALIAS = "dataobs-monitor-definition-history-v1"


def scoped_id(tenant_id: str, environment: str, entity_id: str) -> str:
    if not tenant_id or not environment:
        raise ValueError("tenant_id and environment are mandatory")
    return sha256(f"{tenant_id}\0{environment}\0{entity_id}".encode()).hexdigest()


class ElasticsearchMonitorRepository:
    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    @staticmethod
    def _source(monitor: MonitorDefinition) -> dict[str, Any]:
        return monitor.model_dump(mode="json")

    def create_monitor(self, monitor: MonitorDefinition) -> MonitorDefinition:
        try:
            self.client.create(
                index=MONITORS_ALIAS,
                id=scoped_id(monitor.tenant_id, monitor.environment, monitor.id),
                document=self._source(monitor),
                refresh="wait_for",
            )
        except ConflictError as exc:
            raise VersionConflict("monitor already exists") from exc
        return monitor

    def get_monitor(self, tenant_id: str, environment: str, monitor_id: str) -> MonitorDefinition | None:
        try:
            response = self.client.get(
                index=MONITORS_ALIAS, id=scoped_id(tenant_id, environment, monitor_id), seq_no_primary_term=True
            )
        except NotFoundError:
            return None
        source = response["_source"]
        if source.get("tenant_id") != tenant_id or source.get("environment") != environment:
            return None
        return MonitorDefinition.model_validate(source)

    def update_monitor(self, monitor: MonitorDefinition, *, expected_etag: str) -> MonitorDefinition:
        document_id = scoped_id(monitor.tenant_id, monitor.environment, monitor.id)
        try:
            current = self.client.get(index=MONITORS_ALIAS, id=document_id, seq_no_primary_term=True)
            if current["_source"].get("etag") != expected_etag:
                raise VersionConflict("stale monitor ETag")
            self.client.index(
                index=MONITORS_ALIAS,
                id=document_id,
                document=self._source(monitor),
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError as exc:
            raise VersionConflict("concurrent monitor update") from exc
        return monitor

    def append_definition_event(self, monitor: MonitorDefinition, *, actor: str, action: str) -> None:
        event_id = scoped_id(monitor.tenant_id, monitor.environment, f"{monitor.id}:{monitor.revision}")
        document = {
            "tenant_id": monitor.tenant_id,
            "environment": monitor.environment,
            "monitor_id": monitor.id,
            "revision": monitor.revision,
            "etag": monitor.etag,
            "actor": actor,
            "action": action,
            "definition": self._source(monitor),
        }
        try:
            self.client.create(index=DEFINITION_HISTORY_ALIAS, id=event_id, document=document)
        except ConflictError:
            # Exact lifecycle replay is idempotent; a differing revision is impossible
            # because the immutable ID includes that revision.
            return
