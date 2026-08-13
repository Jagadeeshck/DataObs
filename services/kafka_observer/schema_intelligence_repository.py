"""Elasticsearch persistence for the schema-intelligence reconciliation runtime.

Only derived metadata crosses this boundary.  In particular, repository methods
do not accept schema bodies, which makes accidental raw-schema persistence much
harder than relying on callers to redact them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from elasticsearch import ConflictError, NotFoundError

from services.kafka_observer.intelligence_repository import canonical_id
from services.kafka_observer.reliability_runtime import StaleWriter

SUBJECTS = "dataobs-stream-schema-subject-current-v1"
VERSIONS = "dataobs-stream-schema-version-current-v1"
BINDINGS = "dataobs-stream-schema-binding-current-v1"
IMPACTS = "dataobs-stream-schema-impact-current-v1"
RUNTIME = "dataobs-stream-schema-runtime-state-v1"
VERSION_EVENTS = "logs-dataobs.stream-schema-version-default"
CHANGE_EVENTS = "logs-dataobs.stream-schema-change-default"
COMPATIBILITY_EVENTS = "logs-dataobs.stream-schema-compatibility-default"
IMPACT_EVENTS = "logs-dataobs.stream-schema-consumer-impact-default"


class ElasticsearchSchemaIntelligenceRepository:
    """Fixed-index, tenant-scoped persistence with append idempotency and OCC."""

    MAX_PAGE = 200
    _FORBIDDEN = frozenset({"schema", "raw_schema", "payload", "sample", "message_key", "exception"})

    def __init__(self, es: Any):
        self.es = es

    @classmethod
    def _safe(cls, document: dict[str, Any]) -> dict[str, Any]:
        offending = cls._FORBIDDEN.intersection(document)
        if offending:
            raise ValueError(f"raw schema persistence forbidden: {sorted(offending)[0]}")
        return document

    def append(self, stream: str, event_id: str, document: dict[str, Any], token: int) -> bool:
        self.validate_fence(document["tenant_id"], document["environment"], token)
        try:
            self.es.index(
                index=stream, id=event_id, document=self._safe(document), op_type="create", refresh="wait_for"
            )
            return True
        except ConflictError:
            return False

    def project(self, index: str, identifier: str, document: dict[str, Any], token: int) -> None:
        tenant, environment = document["tenant_id"], document["environment"]
        self.validate_fence(tenant, environment, token)
        try:
            current = self.es.get(index=index, id=identifier, seq_no_primary_term=True)
        except NotFoundError:
            try:
                self.es.index(
                    index=index, id=identifier, document=self._safe(document), op_type="create", refresh="wait_for"
                )
            except ConflictError:
                raise StaleWriter("schema projection concurrently created") from None
            return
        try:
            self.es.index(
                index=index,
                id=identifier,
                document=self._safe(document),
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("schema projection OCC conflict") from None

    def acquire_lease(self, tenant: str, environment: str, worker: str, expires_at: datetime) -> int | None:
        identifier = canonical_id("schema-lease", tenant, environment)
        now = datetime.now(timezone.utc).isoformat()
        result = self.es.update(
            index=RUNTIME,
            id=identifier,
            scripted_upsert=True,
            script={
                "source": "if (ctx._source.lease_expiry != null && ctx._source.lease_expiry.compareTo(params.now)>0 && ctx._source.worker_id!=params.worker) {ctx.op='none'} else {ctx._source.worker_id=params.worker;ctx._source.lease_expiry=params.expiry;ctx._source.fencing_token=(ctx._source.fencing_token ?: 0)+1;ctx._source.heartbeat_at=params.now}",
                "params": {"now": now, "worker": worker, "expiry": expires_at.isoformat()},
            },
            upsert={
                "tenant_id": tenant,
                "environment": environment,
                "worker_id": worker,
                "lease_expiry": expires_at.isoformat(),
                "fencing_token": 1,
                "heartbeat_at": now,
            },
            refresh="wait_for",
        )
        if result.get("result") == "noop":
            return None
        return int(self.es.get(index=RUNTIME, id=identifier)["_source"]["fencing_token"])

    def validate_fence(self, tenant: str, environment: str, token: int) -> None:
        source = self.es.get(index=RUNTIME, id=canonical_id("schema-lease", tenant, environment))["_source"]
        if int(source.get("fencing_token", -1)) != token:
            raise StaleWriter("schema lease fencing token is stale")

    def checkpoint(self, tenant: str, environment: str, cursor: str, worker: str, token: int) -> None:
        self.project(
            RUNTIME,
            canonical_id("schema-checkpoint", tenant, environment),
            {
                "tenant_id": tenant,
                "environment": environment,
                "worker_id": worker,
                "fencing_token": token,
                "checkpoint": cursor,
                "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                "collection_state": "ready",
                "projection_state": "ready",
                "configured": True,
            },
            token,
        )

    def search(
        self, index: str, tenant: str, environment: str, *, subject_id: str | None = None, size: int = 100
    ) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]
        if subject_id:
            filters.append({"term": {"subject_id": subject_id}})
        response = self.es.search(
            index=index,
            size=min(max(size, 1), self.MAX_PAGE),
            query={"bool": {"filter": filters}},
            sort=[{"observed_at": "desc"}, {"event_id": "asc"}],
            timeout="5s",
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
