from __future__ import annotations

from typing import Any

from elasticsearch import ConflictError, NotFoundError

from .contracts import FloodDecision
from .repository import FloodRepository, NotificationDecision, StoredFlood
from .storage import document_to_flood, flood_to_document

FLOOD_ALIAS = "dataobs-incident-suppressions-write"
FLOOD_READ_ALIAS = "dataobs-incident-suppressions-read"
STREAM = "logs-dataobs.incident_suppression-default"
PATTERN = "logs-dataobs.incident_suppression-*"


class ElasticsearchFloodRepository(FloodRepository):
    def __init__(self, client: Any) -> None:
        self.client = client

    @staticmethod
    def _scope(t: str, e: str) -> list[dict[str, Any]]:
        return [{"term": {"tenant_id": t}}, {"term": {"environment": e}}]

    def get_window(self, tenant_id: str, environment: str, flood_id: str) -> StoredFlood | None:
        try:
            hit = self.client.get(index=FLOOD_READ_ALIAS, id=flood_id)
        except NotFoundError:
            return None
        if (hit["_source"].get("tenant_id"), hit["_source"].get("environment")) != (tenant_id, environment):
            return None
        return document_to_flood(hit["_source"], hit["_seq_no"], hit["_primary_term"])

    def create_window(self, stored: StoredFlood) -> StoredFlood:
        r = self.client.create(
            index=FLOOD_ALIAS, id=stored.window.flood_id, document=flood_to_document(stored), refresh="wait_for"
        )
        return StoredFlood(stored.window, stored.projection, r["_seq_no"], r["_primary_term"])

    def update_window(self, stored: StoredFlood) -> StoredFlood:
        r = self.client.index(
            index=FLOOD_ALIAS,
            id=stored.window.flood_id,
            document=flood_to_document(stored),
            if_seq_no=stored.seq_no,
            if_primary_term=stored.primary_term,
            refresh="wait_for",
        )
        return StoredFlood(stored.window, stored.projection, r["_seq_no"], r["_primary_term"])

    def _append(self, event_id: str, document: dict[str, Any]) -> bool:
        try:
            self.client.create(index=STREAM, id=event_id, document=document, refresh="wait_for")
            return True
        except ConflictError:
            return False

    def append_transition(
        self, tenant_id: str, environment: str, event_id: str, flood_id: str, decision: FloodDecision
    ) -> bool:
        return self._append(
            event_id,
            {
                "@timestamp": decision.window_end.isoformat(),
                "tenant_id": tenant_id,
                "environment": environment,
                "correlation_id": event_id,
                "correlation_key": flood_id,
                "correlation_version": decision.policy_version,
                "status": decision.new_state.value,
                "action_type": decision.notification_decision,
                "reason_code": decision.reason_codes[0],
                "metadata": {
                    "reason_codes": decision.reason_codes,
                    "prior_state": decision.prior_state.value,
                    "observed": decision.observed,
                    "thresholds": decision.thresholds,
                },
            },
        )

    def append_notification(self, tenant_id: str, environment: str, decision: NotificationDecision) -> bool:
        return self._append(
            decision.decision_id,
            {
                "@timestamp": decision.created_at.isoformat(),
                "tenant_id": tenant_id,
                "environment": environment,
                "correlation_id": decision.decision_id,
                "correlation_key": decision.flood_id,
                "correlation_version": decision.policy_version,
                "incident_id": decision.representative_incident_id,
                "status": decision.status,
                "action_type": decision.action,
                "reason_code": decision.reason_codes[0],
                "metadata": {
                    "group_id": decision.group_id,
                    "reason_codes": decision.reason_codes,
                    "eligibility_at": decision.eligibility_at.isoformat(),
                    "idempotency_key": decision.idempotency_key,
                },
            },
        )

    def list_storms(self, tenant_id: str, environment: str, *, limit: int = 25) -> list[StoredFlood]:
        r = self.client.search(
            index=FLOOD_READ_ALIAS,
            size=min(limit, 100),
            timeout="2s",
            query={"bool": {"filter": self._scope(tenant_id, environment)}},
            sort=[{"last_observed_at": "desc"}, {"correlation_id": "asc"}],
            seq_no_primary_term=True,
        )
        return [document_to_flood(h["_source"], h["_seq_no"], h["_primary_term"]) for h in r["hits"]["hits"]]

    def list_timeline(
        self, tenant_id: str, environment: str, flood_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        r = self.client.search(
            index=PATTERN,
            size=min(limit, 100),
            timeout="2s",
            query={"bool": {"filter": self._scope(tenant_id, environment) + [{"term": {"correlation_key": flood_id}}]}},
            sort=[{"@timestamp": "asc"}, {"correlation_id": "asc"}],
        )
        return [
            {
                "event_id": h["_source"]["correlation_id"],
                "timestamp": h["_source"]["@timestamp"],
                "state": h["_source"]["status"],
                "action": h["_source"].get("action_type"),
                "reason_codes": h["_source"].get("metadata", {}).get("reason_codes", []),
            }
            for h in r["hits"]["hits"]
        ]
