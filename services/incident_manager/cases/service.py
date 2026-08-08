from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from integrations.elastic.kibana.client import KibanaClient
from integrations.elastic.kibana.errors import KibanaOutcomeUnknown

from .contracts import CaseLink, CaseLinkState
from .repository import CaseLinkRepository

MAX_TITLE = 160
MAX_DESCRIPTION = 3000


def deterministic_reference(tenant_id: str, environment: str, incident_id: str, space: str) -> str:
    material = "\x1f".join((tenant_id, environment, incident_id, space)).encode()
    return "dataobs-ref-" + hashlib.sha256(material).hexdigest()[:24]


class CaseService:
    """One managed Observability Case per scoped incident and configured space."""

    def __init__(self, client: KibanaClient, repository: CaseLinkRepository) -> None:
        self.client, self.repository = client, repository

    def create(
        self,
        *,
        tenant_id: str,
        environment: str,
        incident_id: str,
        actor: str,
        request_id: str,
        title: str,
        description: str,
        severity: str,
    ) -> CaseLink:
        space = self.client.configuration.space_for(environment)
        reference = deterministic_reference(tenant_id, environment, incident_id, space)
        link = self.repository.reserve(
            CaseLink(
                link_id=reference,
                tenant_id=tenant_id,
                environment=environment,
                incident_id=incident_id,
                kibana_space=space,
                reconciliation_reference=reference,
                creation_actor=actor[:200],
                request_id=request_id[:128],
                state=CaseLinkState.CREATE_RESERVED,
            )
        )
        if link.state != CaseLinkState.CREATE_RESERVED:
            return link
        body = {
            "title": title[:MAX_TITLE],
            "description": description[:MAX_DESCRIPTION],
            "owner": "observability",
            "connector": {"id": "none", "name": "none", "type": ".none", "fields": None},
            "settings": {"syncAlerts": False},
            "tags": ["dataobs-managed", "dataobs-incident", f"severity-{severity.lower()[:20]}", reference],
        }
        try:
            remote = self.client.create_case(space, body, request_id)
        except KibanaOutcomeUnknown:
            link.state = CaseLinkState.CREATE_RECONCILIATION_REQUIRED
            return self.repository.update(link, link.revision)
        case_id = remote.get("id")
        if not isinstance(case_id, str) or not case_id:
            link.state = CaseLinkState.CREATE_RECONCILIATION_REQUIRED
            return self.repository.update(link, link.revision)
        link.state = CaseLinkState.LINKED
        link.elastic_case_id = case_id[:256]
        link.elastic_case_version = str(remote.get("version", ""))[:128] or None
        link.case_status = str(remote.get("status", "open"))[:32]
        link.case_severity = str(remote.get("severity", severity))[:32]
        link.sync_state = "in_sync"
        link.last_successful_sync = datetime.now(timezone.utc)
        return self.repository.update(link, link.revision)

    def refresh(self, link: CaseLink) -> CaseLink:
        if link.state != CaseLinkState.LINKED or not link.elastic_case_id:
            return link
        remote: dict[str, Any] = self.client.get_case(link.kibana_space, link.elastic_case_id)
        if remote.get("owner") != "observability" or link.reconciliation_reference not in remote.get("tags", []):
            raise ValueError("remote Case identity mismatch")
        link.case_status = str(remote.get("status", ""))[:32]
        link.case_severity = str(remote.get("severity", ""))[:32]
        link.assignees = tuple(
            str(value.get("uid", ""))[:128] for value in remote.get("assignees", [])[:25] if isinstance(value, dict)
        )
        link.elastic_case_version = str(remote.get("version", ""))[:128]
        link.last_successful_sync = datetime.now(timezone.utc)
        link.sync_state = "in_sync"
        return self.repository.update(link, link.revision)
