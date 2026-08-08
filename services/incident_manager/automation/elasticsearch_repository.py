from __future__ import annotations

from datetime import datetime
from typing import Any

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from .contracts import Approval, Execution, Preview
from .repository import Conflict

APPROVAL_READ = "dataobs-action-approvals-v1-read"
APPROVAL_WRITE = "dataobs-action-approvals-v1-write"
OPERATION_READ = "dataobs-action-idempotency-v1-read"
OPERATION_WRITE = "dataobs-action-idempotency-v1-write"
STREAMS = {
    "approval_event": "logs-dataobs.approval_event-default",
    "remediation_action": "logs-dataobs.remediation_action-default",
    "verification_event": "logs-dataobs.verification_event-default",
}


def _approval_document(item: Approval) -> dict[str, Any]:
    return {
        "tenant_id": item.tenant_id,
        "environment": item.environment,
        "incident_id": item.incident_id,
        "action_type": item.action_type,
        "risk_level": item.risk.value,
        "approval_state": item.state.value,
        "request_id": item.request_id,
        "revision": item.revision,
        "created_at": item.requested_at.isoformat(),
        "updated_at": datetime.now(item.requested_at.tzinfo).isoformat(),
        "expires_at": item.expires_at.isoformat(),
        "terminal_state": item.state.value in {"rejected", "expired", "cancelled", "consumed"},
        "metadata": item.model_dump(mode="json"),
    }


def _execution_document(item: Execution, idempotency_fingerprint: str | None = None) -> dict[str, Any]:
    metadata = item.model_dump(mode="json")
    if idempotency_fingerprint:
        metadata["idempotency_fingerprint"] = idempotency_fingerprint
    return {
        "tenant_id": item.tenant_id,
        "environment": item.environment,
        "incident_id": item.incident_id,
        "workflow_execution_id": item.execution_id,
        "action_type": item.action_type,
        "status": item.state.value,
        "request_id": item.request_id,
        "retry_count": max(item.attempt - 1, 0),
        "timeout_seconds": item.timeout_seconds,
        "terminal_state": item.state.value in {"verified", "verification_failed", "failed", "timed_out", "cancelled"},
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "metadata": metadata,
    }


class ElasticsearchAutomationRepository:
    """Strict-mapping adapter; all supplementary contract values stay in bounded flattened metadata."""

    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    def save_preview(self, preview: Preview) -> Preview:
        # Previews are immutable and stored with operation state; create makes retries idempotent.
        doc = {
            "tenant_id": preview.tenant_id,
            "environment": preview.environment,
            "incident_id": preview.incident_id,
            "action_type": preview.action_type,
            "status": "previewed",
            "request_id": preview.request_id,
            "terminal_state": False,
            "created_at": preview.previewed_at.isoformat(),
            "updated_at": preview.previewed_at.isoformat(),
            "metadata": preview.model_dump(mode="json"),
        }
        try:
            self.client.create(index=OPERATION_WRITE, id=preview.preview_id, document=doc, refresh="wait_for")
        except ConflictError:
            pass
        return preview

    def _get_metadata(self, alias: str, document_id: str, tenant: str, environment: str) -> dict[str, Any] | None:
        try:
            hit = self.client.get(index=alias, id=document_id)
        except NotFoundError:
            return None
        source = hit["_source"]
        if (source.get("tenant_id"), source.get("environment")) != (tenant, environment):
            return None
        metadata = dict(source.get("metadata", {}))
        metadata["_seq_no"], metadata["_primary_term"] = hit["_seq_no"], hit["_primary_term"]
        return metadata

    def get_preview(self, tenant_id: str, environment: str, preview_id: str) -> Preview | None:
        data = self._get_metadata(OPERATION_READ, preview_id, tenant_id, environment)
        if not data:
            return None
        data.pop("_seq_no", None)
        data.pop("_primary_term", None)
        return Preview.model_validate(data)

    def create_approval(self, approval: Approval) -> Approval:
        try:
            self.client.create(
                index=APPROVAL_WRITE, id=approval.approval_id, document=_approval_document(approval), refresh="wait_for"
            )
            return approval
        except ConflictError:
            current = self.get_approval(approval.tenant_id, approval.environment, approval.approval_id)
            if not current or current.action_fingerprint != approval.action_fingerprint:
                raise Conflict("approval idempotency conflict")
            return current

    def get_approval(self, tenant_id: str, environment: str, approval_id: str) -> Approval | None:
        data = self._get_metadata(APPROVAL_READ, approval_id, tenant_id, environment)
        if not data:
            return None
        data.pop("_seq_no", None)
        data.pop("_primary_term", None)
        return Approval.model_validate(data)

    def update_approval(self, approval: Approval, expected_revision: int) -> Approval:
        data = self._get_metadata(APPROVAL_READ, approval.approval_id, approval.tenant_id, approval.environment)
        if not data or int(data.get("revision", -1)) != expected_revision:
            raise Conflict("approval revision conflict")
        seq, term = data.pop("_seq_no"), data.pop("_primary_term")
        approval.revision = expected_revision + 1
        try:
            self.client.index(
                index=APPROVAL_WRITE,
                id=approval.approval_id,
                document=_approval_document(approval),
                if_seq_no=seq,
                if_primary_term=term,
                refresh="wait_for",
            )
        except ConflictError as exc:
            raise Conflict("approval revision conflict") from exc
        return approval

    def create_execution(self, execution: Execution, idempotency_fingerprint: str) -> Execution:
        try:
            self.client.create(
                index=OPERATION_WRITE,
                id=execution.execution_id,
                document=_execution_document(execution, idempotency_fingerprint),
                refresh="wait_for",
            )
            return execution
        except ConflictError:
            current = self.get_execution(execution.tenant_id, execution.environment, execution.execution_id)
            data = self._get_metadata(
                OPERATION_READ, execution.execution_id, execution.tenant_id, execution.environment
            )
            if not current or not data or data.get("idempotency_fingerprint") != idempotency_fingerprint:
                raise Conflict("idempotency key conflict")
            return current

    def get_execution(self, tenant_id: str, environment: str, execution_id: str) -> Execution | None:
        data = self._get_metadata(OPERATION_READ, execution_id, tenant_id, environment)
        if not data:
            return None
        data.pop("_seq_no", None)
        data.pop("_primary_term", None)
        data.pop("idempotency_fingerprint", None)
        return Execution.model_validate(data)

    def update_execution(self, execution: Execution, expected_lease_token: int | None = None) -> Execution:
        data = self._get_metadata(OPERATION_READ, execution.execution_id, execution.tenant_id, execution.environment)
        if not data or (expected_lease_token is not None and int(data.get("lease_token", -1)) != expected_lease_token):
            raise Conflict("execution fence conflict")
        seq, term = data.pop("_seq_no"), data.pop("_primary_term")
        idem = data.get("idempotency_fingerprint")
        try:
            self.client.index(
                index=OPERATION_WRITE,
                id=execution.execution_id,
                document=_execution_document(execution, idem),
                if_seq_no=seq,
                if_primary_term=term,
                refresh="wait_for",
            )
        except ConflictError as exc:
            raise Conflict("execution fence conflict") from exc
        return execution

    def queued(self, limit: int, now: datetime) -> list[Execution]:
        response = self.client.search(
            index=OPERATION_READ,
            size=min(max(limit, 1), 25),
            query={"term": {"status": "queued"}},
            sort=[{"created_at": "asc"}, {"workflow_execution_id": "asc"}],
        )
        return [
            Execution.model_validate(
                {k: v for k, v in hit["_source"]["metadata"].items() if k != "idempotency_fingerprint"}
            )
            for hit in response["hits"]["hits"]
        ]

    def append_event(self, stream: str, event_id: str, document: dict[str, object]) -> None:
        try:
            self.client.create(index=STREAMS[stream], id=event_id, document=document, refresh="wait_for")
        except ConflictError:
            pass
