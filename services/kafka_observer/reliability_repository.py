"""Tenant-safe Elasticsearch persistence for the Team 1 reliability runtime."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from elasticsearch import ConflictError, NotFoundError

from packages.streaming.reliability import Definition, Evaluation, PreviousState, Status
from services.kafka_observer.reliability_runtime import StaleWriter

DEFINITIONS = "dataobs-stream-slo-definitions-v1-write"
DEFINITIONS_READ = "dataobs-stream-slo-definitions-v1-read"
STATUS = "dataobs-reliability-status-v1-write"
STATUS_READ = "dataobs-reliability-status-v1-read"
RUNTIME = "dataobs-reliability-runtime-state-v1-write"
STREAM_EVALUATIONS = "metrics-dataobs.stream-slo-evaluation-default"
PATHWAY_EVALUATIONS = "metrics-dataobs.pathway-slo-evaluation-default"
SIGNALS = "logs-dataobs.reliability-signal-default"


class ElasticsearchReliabilityRepository:
    """Bounded repository; all public reads require trusted scope arguments."""

    MAX_PAGE = 200

    def __init__(self, es: Any):
        self.es = es

    @staticmethod
    def _definition(source: dict[str, Any]) -> Definition:
        allowed = Definition.__dataclass_fields__.keys()
        return Definition(**{key: source[key] for key in allowed})

    def acquire(self, scope: str, worker: str, expires_at: datetime) -> int | None:
        now = datetime.now(timezone.utc).isoformat()
        script = {
            "source": """if (ctx._source.expires_at.compareTo(params.now) > 0 && ctx._source.worker_id != params.worker) {ctx.op='none'} else {ctx._source.worker_id=params.worker; ctx._source.expires_at=params.expires; ctx._source.fencing_token=(ctx._source.fencing_token ?: 0)+1; ctx._source.updated_at=params.now}""",
            "params": {"now": now, "worker": worker, "expires": expires_at.isoformat()},
        }
        result = self.es.update(
            index=RUNTIME,
            id=f"lease:{scope}",
            script=script,
            scripted_upsert=True,
            upsert={"worker_id": worker, "expires_at": expires_at.isoformat(), "fencing_token": 1, "updated_at": now},
            refresh="wait_for",
        )
        if result.get("result") == "noop":
            return None
        return int(self.es.get(index=RUNTIME, id=f"lease:{scope}")["_source"]["fencing_token"])

    def renew(self, scope: str, worker: str, token: int, expires_at: datetime) -> None:
        self._assert_fence(scope, token, worker)
        self.es.update(index=RUNTIME, id=f"lease:{scope}", doc={"expires_at": expires_at.isoformat()})

    def release(self, scope: str, worker: str, token: int) -> None:
        self._assert_fence(scope, token, worker)
        self.es.update(index=RUNTIME, id=f"lease:{scope}", doc={"expires_at": datetime.now(timezone.utc).isoformat()})

    def _assert_fence(self, scope: str, token: int, worker: str | None = None) -> None:
        source = self.es.get(index=RUNTIME, id=f"lease:{scope}")["_source"]
        if int(source.get("fencing_token", -1)) != token or (worker and source.get("worker_id") != worker):
            raise StaleWriter("lease fencing token is stale")

    def due(self, tenant: str, environment: str, now: datetime, limit: int) -> list[Definition]:
        size = min(max(limit, 1), self.MAX_PAGE)
        response = self.es.search(
            index=DEFINITIONS_READ,
            size=size,
            sort=[{"next_evaluation_at": "asc"}, {"id": "asc"}],
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {"term": {"enabled": True}},
                        {"range": {"next_evaluation_at": {"lte": now.isoformat()}}},
                    ]
                }
            },
            source=list(Definition.__dataclass_fields__),
        )
        return [self._definition(hit["_source"]) for hit in response["hits"]["hits"]]

    def previous(self, definition: Definition) -> PreviousState:
        try:
            source = self.es.get(index=STATUS_READ, id=self.status_id(definition))["_source"]
        except NotFoundError:
            return PreviousState()
        if source.get("tenant_id") != definition.tenant_id or source.get("environment") != definition.environment:
            return PreviousState()
        first = source.get("first_breach_at")
        return PreviousState(
            Status(source["current_status"]),
            int(source.get("consecutive_breaches", 0)),
            int(source.get("consecutive_recoveries", 0)),
            datetime.fromisoformat(first) if first else None,
        )

    @staticmethod
    def status_id(definition: Definition) -> str:
        raw = f"{definition.tenant_id}\0{definition.environment}\0{definition.id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def persist(self, evaluation: Evaluation, definition: Definition, fencing_token: int) -> bool:
        self._assert_fence(f"{definition.tenant_id}:{definition.environment}", fencing_token)
        document = asdict(evaluation) | {
            "tenant_id": definition.tenant_id,
            "environment": definition.environment,
            "resource_type": definition.resource_type,
            "resource_id": definition.resource_id,
            "metric": definition.metric,
            "threshold": definition.threshold,
            "operator": definition.operator,
            "schema_version": "v1",
            "@timestamp": evaluation.evaluated_at,
        }
        try:
            self.es.index(
                index=PATHWAY_EVALUATIONS if definition.resource_type == "pathway" else STREAM_EVALUATIONS,
                id=evaluation.evaluation_id,
                document=document,
                op_type="create",
                refresh="wait_for",
            )
        except ConflictError:
            return False
        return True

    def project(self, evaluation: Evaluation, definition: Definition, fencing_token: int) -> None:
        self._assert_fence(f"{definition.tenant_id}:{definition.environment}", fencing_token)
        doc_id = self.status_id(definition)
        document = asdict(evaluation) | {
            "status_id": doc_id,
            "definition_id": definition.id,
            "tenant_id": definition.tenant_id,
            "environment": definition.environment,
            "resource_type": definition.resource_type,
            "resource_id": definition.resource_id,
            "metric": definition.metric,
            "threshold": definition.threshold,
            "operator": definition.operator,
            "unit": "unknown",
            "current_status": evaluation.status.value,
            "previous_status": evaluation.previous_status.value,
            "latest_evaluation_id": evaluation.evaluation_id,
            "transition_at": evaluation.evaluated_at,
            "revision": 1,
            "schema_version": "v1",
        }
        try:
            current = self.es.get(index=STATUS_READ, id=doc_id, seq_no_primary_term=True)
        except NotFoundError:
            try:
                self.es.index(index=STATUS, id=doc_id, document=document, op_type="create", refresh="wait_for")
            except ConflictError:
                raise StaleWriter("status projection was concurrently created") from None
            return
        document["revision"] = int(current["_source"].get("revision", 0)) + 1
        try:
            self.es.index(
                index=STATUS,
                id=doc_id,
                document=document,
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("status projection OCC conflict") from None

    def signal(self, evaluation: Evaluation, definition: Definition, fencing_token: int) -> None:
        self._assert_fence(f"{definition.tenant_id}:{definition.environment}", fencing_token)
        transition = None
        if evaluation.status == Status.BREACHING and evaluation.previous_status != Status.BREACHING:
            transition = "breach"
        elif evaluation.status == Status.HEALTHY and evaluation.previous_status in {
            Status.BREACHING,
            Status.RECOVERING,
        }:
            transition = "recovery"
        if transition is None:
            return
        signal_id = hashlib.sha256(
            f"{definition.tenant_id}\0{definition.environment}\0{definition.id}\0{transition}\0{evaluation.evaluation_id}".encode()
        ).hexdigest()
        self.persist_signal(
            {
                "signal_id": signal_id,
                "definition_id": definition.id,
                "tenant_id": definition.tenant_id,
                "environment": definition.environment,
                "resource_type": definition.resource_type,
                "resource_id": definition.resource_id,
                "metric": definition.metric,
                "previous_status": evaluation.previous_status.value,
                "current_status": evaluation.status.value,
                "observed_value": evaluation.observed_value,
                "threshold": definition.threshold,
                "operator": definition.operator,
                "severity": "critical" if transition == "breach" else "resolved",
                "first_breach_at": evaluation.first_breach_at,
                "transition_at": evaluation.evaluated_at,
                "latest_evaluation_id": evaluation.evaluation_id,
                "reason_codes": evaluation.reason_codes,
                "evidence_refs": evaluation.evidence_refs,
                "confidence": evaluation.confidence,
                "source_coverage": evaluation.source_coverage,
                "schema_version": "v1",
                "@timestamp": evaluation.evaluated_at,
            }
        )

    def checkpoint(self, definition: Definition, evaluation_id: str, fencing_token: int, now: datetime) -> None:
        self._assert_fence(f"{definition.tenant_id}:{definition.environment}", fencing_token)
        from datetime import timedelta

        current = self.es.get(index=DEFINITIONS_READ, id=definition.id, seq_no_primary_term=True)
        next_at = (now.astimezone(timezone.utc) + timedelta(seconds=definition.evaluation_interval_seconds)).isoformat()
        try:
            self.es.update(
                index=DEFINITIONS,
                id=definition.id,
                doc={"latest_evaluation_id": evaluation_id, "next_evaluation_at": next_at},
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("definition checkpoint OCC conflict") from None

    def persist_health(self, scope: str, health: Any, fencing_token: int) -> None:
        self._assert_fence(scope, fencing_token, health.worker_id)
        document = asdict(health) | {
            "scope": scope,
            "heartbeat_at": datetime.now(timezone.utc),
            "runtime_version": "v1",
            "lease_owner": health.worker_id,
        }
        self.es.index(index=RUNTIME, id=f"health:{scope}", document=document, refresh="wait_for")

    def runtime_health(self, tenant: str, environment: str) -> dict[str, Any] | None:
        try:
            return self.es.get(index=RUNTIME, id=f"health:{tenant}:{environment}")["_source"]
        except NotFoundError:
            return None

    def inventory(
        self, tenant: str, environment: str, *, size: int = 100, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        clauses = [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]
        for key, value in (filters or {}).items():
            if key in {"resource_type", "resource_id", "metric", "enabled", "owner"} and value is not None:
                clauses.append({"term": {key: value}})
        result = self.es.search(
            index=DEFINITIONS_READ,
            size=min(size, self.MAX_PAGE),
            query={"bool": {"filter": clauses}},
            sort=[{"updated_at": "desc"}, {"id": "asc"}],
            source_excludes=["created_actor", "updated_actor"],
        )
        return [hit["_source"] for hit in result["hits"]["hits"]]

    def evaluations(self, definition: Definition, size: int = 50) -> list[dict[str, Any]]:
        index = PATHWAY_EVALUATIONS if definition.resource_type == "pathway" else STREAM_EVALUATIONS
        result = self.es.search(
            index=index,
            size=min(size, self.MAX_PAGE),
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": definition.tenant_id}},
                        {"term": {"environment": definition.environment}},
                        {"term": {"definition_id": definition.id}},
                    ]
                }
            },
            sort=[{"evaluated_at": "desc"}, {"evaluation_id": "asc"}],
            source_excludes=["evidence"],
        )
        return [hit["_source"] for hit in result["hits"]["hits"]]

    def current_status(self, definition: Definition) -> dict[str, Any] | None:
        try:
            source = self.es.get(index=STATUS_READ, id=self.status_id(definition), source_excludes=["evidence"])[
                "_source"
            ]
        except NotFoundError:
            return None
        if source.get("tenant_id") != definition.tenant_id or source.get("environment") != definition.environment:
            return None
        return source

    def summary(self, tenant: str, environment: str) -> dict[str, int]:
        statuses = [status.value for status in Status]
        result = self.es.search(
            index=STATUS_READ,
            size=0,
            query={"bool": {"filter": [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]}},
            aggs={"statuses": {"terms": {"field": "current_status", "size": len(statuses)}}},
        )
        counts = {status: 0 for status in statuses}
        counts.update({bucket["key"]: bucket["doc_count"] for bucket in result["aggregations"]["statuses"]["buckets"]})
        return counts

    def persist_signal(self, signal: dict[str, Any]) -> bool:
        try:
            self.es.index(index=SIGNALS, id=signal["signal_id"], document=signal, op_type="create", refresh="wait_for")
            return True
        except ConflictError:
            return False
