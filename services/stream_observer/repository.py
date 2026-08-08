from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from elasticsearch import ConflictError

EVIDENCE_STREAMS = {
    "resource": "metrics-dataobs.messaging-resource-default",
    "backlog": "metrics-dataobs.messaging-backlog-default",
    "throughput": "metrics-dataobs.messaging-throughput-default",
    "delivery": "metrics-dataobs.messaging-delivery-default",
}
PROJECTION_INDICES = {
    "resource": "dataobs-messaging-resources-v1",
    "backlog": "dataobs-messaging-backlog-current-v1",
    "throughput": "dataobs-messaging-throughput-current-v1",
    "delivery": "dataobs-messaging-delivery-current-v1",
}


class FenceRejected(RuntimeError):
    pass


def canonical_evidence_id(document: dict[str, Any], family: str) -> str:
    parts = (
        document["tenant_id"],
        document["environment"],
        document["resource_id"],
        family,
        str(document["observed_at"]),
        document["source_integration"],
    )
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def checkpoint_id(scope: dict[str, str]) -> str:
    required = (
        "tenant_id",
        "environment",
        "provider_integration",
        "messaging_system",
        "observation_family",
        "resource_scope",
    )
    return hashlib.sha256("\x1f".join(scope[key] for key in required).encode()).hexdigest()


@dataclass(frozen=True)
class VersionedDocument:
    document: dict[str, Any]
    seq_no: int
    primary_term: int


class MessagingRepository:
    """Bounded ES persistence with create-only evidence and OCC projections."""

    def __init__(self, es: Any, *, timeout: float = 5.0):
        self.es = es
        self.timeout = timeout

    def append(self, family: str, document: dict[str, Any]) -> bool:
        evidence_id = canonical_evidence_id(document, family)
        try:
            self.es.create(
                index=EVIDENCE_STREAMS[family], id=evidence_id, document=document, request_timeout=self.timeout
            )
            return True
        except ConflictError:
            return False

    def get_projection(self, family: str, resource_id: str) -> VersionedDocument | None:
        try:
            hit = self.es.get(index=PROJECTION_INDICES[family], id=resource_id, request_timeout=self.timeout)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                return None
            raise
        return VersionedDocument(hit["_source"], hit["_seq_no"], hit["_primary_term"])

    def project(self, family: str, document: dict[str, Any], *, fencing_token: int) -> None:
        current = self.get_projection(family, document["resource_id"])
        if current and int(current.document.get("fencing_token", -1)) > fencing_token:
            raise FenceRejected("stale_fencing_token")
        body = {**document, "fencing_token": fencing_token}
        kwargs: dict[str, Any] = {}
        if current:
            kwargs.update(if_seq_no=current.seq_no, if_primary_term=current.primary_term)
        else:
            kwargs["op_type"] = "create"
        self.es.index(
            index=PROJECTION_INDICES[family],
            id=document["resource_id"],
            document=body,
            request_timeout=self.timeout,
            **kwargs,
        )

    def save_checkpoint(
        self, scope: dict[str, str], document: dict[str, Any], current: VersionedDocument | None
    ) -> None:
        kwargs = (
            {"if_seq_no": current.seq_no, "if_primary_term": current.primary_term} if current else {"op_type": "create"}
        )
        self.es.index(
            index="dataobs-messaging-checkpoints-v1",
            id=checkpoint_id(scope),
            document={**scope, **document},
            request_timeout=self.timeout,
            **kwargs,
        )

    def search_runtime_states(self, tenant_id: str, environment: str) -> list[dict[str, Any]]:
        response = self.es.search(
            index="dataobs-messaging-runtime-state-v1",
            size=100,
            request_timeout=self.timeout,
            query={"bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]}},
            sort=[{"provider": "asc"}, {"messaging_system": "asc"}],
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
