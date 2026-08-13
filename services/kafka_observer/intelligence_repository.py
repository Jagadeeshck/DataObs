"""Production Elasticsearch persistence for Stream Intelligence v1.

The repository deliberately exposes domain operations rather than arbitrary DSL.
Every read is scoped and every mutable replacement uses Elasticsearch OCC.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from elasticsearch import ConflictError, NotFoundError

from packages.streaming.intelligence import DetectorDefinition, DetectorPreviousState, DetectorState
from services.kafka_observer.reliability_runtime import StaleWriter

DEFINITIONS = "dataobs-stream-detector-definitions-v1"
ANOMALIES = "dataobs-stream-anomaly-current-v1"
FORECASTS = "dataobs-stream-retention-forecast-current-v1"
CANDIDATES = "dataobs-stream-failure-candidate-current-v1"
RUNTIME = "dataobs-stream-intelligence-runtime-state-v1"
EVALUATIONS = "metrics-dataobs.stream-anomaly-evaluation-default"
FORECAST_EVIDENCE = "metrics-dataobs.stream-retention-forecast-default"
CANDIDATE_EVIDENCE = "logs-dataobs.stream-failure-candidate-default"
SIGNALS = "logs-dataobs.stream-intelligence-signal-default"
CAPACITY = "dataobs-stream-capacity-current-v1"
CAPACITY_EVIDENCE = "logs-dataobs.stream-capacity-evaluation-default"


def canonical_id(kind: str, tenant: str, environment: str, *parts: object) -> str:
    """Return a collision-safe identity over a length-delimited canonical tuple."""
    values = (tenant, environment, kind, *(str(part) for part in parts))
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _json(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


class ElasticsearchIntelligenceRepository:
    MAX_PAGE = 200

    def __init__(self, es: Any):
        self.es = es

    @staticmethod
    def detector_identity(tenant: str, environment: str, detector_id: str) -> str:
        return canonical_id("detector", tenant, environment, detector_id)

    def create_detector(self, definition: DetectorDefinition, request_fingerprint: str) -> dict[str, Any]:
        document = _json(definition) | {"request_fingerprint": request_fingerprint}
        identifier = self.detector_identity(definition.tenant_id, definition.environment, definition.detector_id)
        try:
            result = self.es.index(
                index=DEFINITIONS, id=identifier, document=document, op_type="create", refresh="wait_for"
            )
            return document | {"_seq_no": result.get("_seq_no"), "_primary_term": result.get("_primary_term")}
        except ConflictError:
            current = self.get_detector(definition.tenant_id, definition.environment, definition.detector_id)
            if current.get("request_fingerprint") != request_fingerprint:
                raise ValueError("idempotency fingerprint conflict") from None
            return current

    def get_detector(self, tenant: str, environment: str, detector_id: str) -> dict[str, Any]:
        identifier = self.detector_identity(tenant, environment, detector_id)
        try:
            hit = self.es.get(index=DEFINITIONS, id=identifier, seq_no_primary_term=True)
        except NotFoundError:
            raise KeyError(detector_id) from None
        source = hit["_source"]
        if source.get("tenant_id") != tenant or source.get("environment") != environment:
            raise KeyError(detector_id)
        return source | {"_seq_no": hit["_seq_no"], "_primary_term": hit["_primary_term"]}

    def update_detector(
        self, tenant: str, environment: str, detector_id: str, changes: dict[str, Any], *, revision: int, actor: str
    ) -> dict[str, Any]:
        current = self.get_detector(tenant, environment, detector_id)
        if int(current.get("revision", 0)) != revision:
            raise StaleWriter("detector revision is stale")
        protected = {"detector_id", "tenant_id", "environment", "created_at", "created_actor", "request_fingerprint"}
        document = {key: value for key, value in current.items() if not key.startswith("_")}
        document.update({key: _json(value) for key, value in changes.items() if key not in protected})
        document.update(revision=revision + 1, updated_actor=actor, updated_at=datetime.now(timezone.utc).isoformat())
        # Re-validate the complete public contract before persistence.
        DetectorDefinition(**{key: document[key] for key in DetectorDefinition.__dataclass_fields__})
        try:
            result = self.es.index(
                index=DEFINITIONS,
                id=self.detector_identity(tenant, environment, detector_id),
                document=document,
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("detector OCC conflict") from None
        return document | {"_seq_no": result.get("_seq_no"), "_primary_term": result.get("_primary_term")}

    def delete_detector(self, tenant: str, environment: str, detector_id: str, *, revision: int) -> None:
        current = self.get_detector(tenant, environment, detector_id)
        if int(current.get("revision", 0)) != revision:
            raise StaleWriter("detector revision is stale")
        try:
            self.es.delete(
                index=DEFINITIONS,
                id=self.detector_identity(tenant, environment, detector_id),
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("detector OCC conflict") from None

    def _search(
        self,
        index: str,
        tenant: str,
        environment: str,
        *,
        size: int,
        sort: list[dict[str, Any]],
        filters: dict[str, Any] | None = None,
        after: list[Any] | None = None,
    ) -> dict[str, Any]:
        clauses: list[dict[str, Any]] = [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]
        for key, value in (filters or {}).items():
            if (
                key in {
                    "detector_id", "resource_type", "resource_id", "metric", "state", "overall_state", "enabled",
                    "classification", "provider", "messaging_system", "bottleneck_dimension", "throttled",
                    "retention_risk",
                }
                and value is not None
            ):
                clauses.append({"term": {key: value}})
        kwargs: dict[str, Any] = {
            "index": index,
            "size": min(max(size, 1), self.MAX_PAGE),
            "sort": sort,
            "query": {"bool": {"filter": clauses}},
            "track_total_hits": True,
        }
        if after:
            kwargs["search_after"] = after
        response = self.es.search(**kwargs)
        hits = response["hits"]["hits"]
        return {
            "items": [hit["_source"] | {"id": hit["_id"]} for hit in hits],
            "last_sort": hits[-1].get("sort") if hits else None,
            "total": response["hits"].get("total", {}).get("value"),
        }

    def list_detectors(
        self,
        tenant: str,
        environment: str,
        *,
        size: int = 50,
        filters: dict[str, Any] | None = None,
        after: list[Any] | None = None,
    ) -> dict[str, Any]:
        return self._search(
            DEFINITIONS,
            tenant,
            environment,
            size=size,
            filters=filters,
            after=after,
            sort=[{"updated_at": "desc"}, {"detector_id": "asc"}],
        )

    def list_due_detectors(self, tenant: str, environment: str, now: datetime, limit: int) -> list[DetectorDefinition]:
        result = self.es.search(
            index=DEFINITIONS,
            size=min(max(limit, 1), self.MAX_PAGE),
            sort=[{"next_evaluation_at": "asc"}, {"detector_id": "asc"}],
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
        )
        return [
            DetectorDefinition(**{key: hit["_source"][key] for key in DetectorDefinition.__dataclass_fields__})
            for hit in result["hits"]["hits"]
        ]

    def load_previous_state(self, definition: DetectorDefinition) -> DetectorPreviousState:
        identifier = canonical_id(
            "anomaly",
            definition.tenant_id,
            definition.environment,
            definition.resource_type,
            definition.resource_id,
            definition.detector_id,
        )
        try:
            source = self.es.get(index=ANOMALIES, id=identifier)["_source"]
        except NotFoundError:
            return DetectorPreviousState()
        return DetectorPreviousState(
            DetectorState(source["state"]),
            int(source.get("consecutive_anomalies", 0)),
            int(source.get("consecutive_recoveries", 0)),
        )

    def append(self, index: str, identifier: str, document: dict[str, Any]) -> bool:
        try:
            self.es.index(index=index, id=identifier, document=_json(document), op_type="create", refresh="wait_for")
        except ConflictError:
            return False
        return True

    def append_evaluation(
        self, definition: DetectorDefinition, evaluation_id: str, document: dict[str, Any], token: int
    ) -> bool:
        self.validate_fencing_token(definition.tenant_id, definition.environment, token)
        return self.append(
            EVALUATIONS,
            canonical_id(
                "evaluation",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
                evaluation_id,
            ),
            document,
        )

    def _project(
        self, index: str, identifier: str, document: dict[str, Any], tenant: str, environment: str, token: int
    ) -> None:
        self.validate_fencing_token(tenant, environment, token)
        try:
            current = self.es.get(index=index, id=identifier, seq_no_primary_term=True)
        except NotFoundError:
            try:
                self.es.index(
                    index=index, id=identifier, document=_json(document), op_type="create", refresh="wait_for"
                )
            except ConflictError:
                raise StaleWriter("projection concurrently created") from None
            return
        try:
            self.es.index(
                index=index,
                id=identifier,
                document=_json(document),
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("projection OCC conflict") from None

    def update_anomaly_projection(self, definition: DetectorDefinition, document: dict[str, Any], token: int) -> None:
        self._project(
            ANOMALIES,
            canonical_id(
                "anomaly",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
            ),
            document,
            definition.tenant_id,
            definition.environment,
            token,
        )

    def persist_forecast(
        self, definition: DetectorDefinition, forecast_id: str, document: dict[str, Any], token: int
    ) -> None:
        self.validate_fencing_token(definition.tenant_id, definition.environment, token)
        self.append(
            FORECAST_EVIDENCE,
            canonical_id(
                "forecast-evidence",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
                forecast_id,
            ),
            document,
        )
        self._project(
            FORECASTS,
            canonical_id(
                "forecast",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
            ),
            document,
            definition.tenant_id,
            definition.environment,
            token,
        )

    def persist_failure_candidate(
        self, definition: DetectorDefinition, candidate_id: str, document: dict[str, Any], token: int
    ) -> None:
        self.validate_fencing_token(definition.tenant_id, definition.environment, token)
        self.append(
            CANDIDATE_EVIDENCE,
            canonical_id(
                "candidate-evidence",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
                candidate_id,
            ),
            document,
        )
        self._project(
            CANDIDATES,
            canonical_id(
                "candidate",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
                candidate_id,
            ),
            document,
            definition.tenant_id,
            definition.environment,
            token,
        )

    def persist_signal(
        self, definition: DetectorDefinition, signal_id: str, document: dict[str, Any], token: int
    ) -> bool:
        self.validate_fencing_token(definition.tenant_id, definition.environment, token)
        return self.append(
            SIGNALS,
            canonical_id(
                "signal",
                definition.tenant_id,
                definition.environment,
                definition.resource_type,
                definition.resource_id,
                definition.detector_id,
                signal_id,
            ),
            document,
        )

    def acquire_lease(self, tenant: str, environment: str, worker: str, expires_at: datetime) -> int | None:
        identifier = canonical_id("lease", tenant, environment)
        now = datetime.now(timezone.utc).isoformat()
        result = self.es.update(
            index=RUNTIME,
            id=identifier,
            scripted_upsert=True,
            script={
                "source": "if (ctx._source.lease_expiry.compareTo(params.now) > 0 && ctx._source.worker_id != params.worker) {ctx.op='none'} else {ctx._source.worker_id=params.worker;ctx._source.lease_expiry=params.expiry;ctx._source.fencing_token=(ctx._source.fencing_token ?: 0)+1;ctx._source.heartbeat_at=params.now}",
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

    def validate_fencing_token(self, tenant: str, environment: str, token: int, worker: str | None = None) -> None:
        source = self.es.get(index=RUNTIME, id=canonical_id("lease", tenant, environment))["_source"]
        if int(source.get("fencing_token", -1)) != token or (worker and source.get("worker_id") != worker):
            raise StaleWriter("lease fencing token is stale")

    def renew_lease(self, tenant: str, environment: str, worker: str, token: int, expires_at: datetime) -> None:
        self.validate_fencing_token(tenant, environment, token, worker)
        current = self.es.get(index=RUNTIME, id=canonical_id("lease", tenant, environment), seq_no_primary_term=True)
        self.es.update(
            index=RUNTIME,
            id=current["_id"],
            doc={"lease_expiry": expires_at.isoformat(), "heartbeat_at": datetime.now(timezone.utc).isoformat()},
            if_seq_no=current["_seq_no"],
            if_primary_term=current["_primary_term"],
            refresh="wait_for",
        )

    def release_lease(self, tenant: str, environment: str, worker: str, token: int) -> None:
        self.renew_lease(tenant, environment, worker, token, datetime.now(timezone.utc))

    def advance_detector_checkpoint(
        self, definition: DetectorDefinition, evaluation_id: str, next_at: datetime, token: int
    ) -> None:
        self.validate_fencing_token(definition.tenant_id, definition.environment, token)
        current = self.get_detector(definition.tenant_id, definition.environment, definition.detector_id)
        try:
            self.es.update(
                index=DEFINITIONS,
                id=self.detector_identity(definition.tenant_id, definition.environment, definition.detector_id),
                doc={"latest_evaluation_id": evaluation_id, "next_evaluation_at": next_at.isoformat()},
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError:
            raise StaleWriter("checkpoint OCC conflict") from None

    def persist_runtime_health(self, tenant: str, environment: str, health: dict[str, Any], token: int) -> None:
        self.validate_fencing_token(tenant, environment, token, health.get("worker_id"))
        self._project(
            RUNTIME,
            canonical_id("runtime", tenant, environment),
            _json(health) | {"tenant_id": tenant, "environment": environment},
            tenant,
            environment,
            token,
        )

    def runtime_health(self, tenant: str, environment: str) -> dict[str, Any] | None:
        try:
            source = self.es.get(index=RUNTIME, id=canonical_id("runtime", tenant, environment))["_source"]
        except NotFoundError:
            return None
        return source if source.get("tenant_id") == tenant and source.get("environment") == environment else None

    def append_capacity_evaluation(self, document: dict[str, Any], token: int) -> None:
        self.validate_fencing_token(document["tenant_id"], document["environment"], token)
        self.es.index(index=CAPACITY_EVIDENCE, id=document["evaluation_id"], document=_json(document), op_type="create")

    def project_capacity(self, document: dict[str, Any], token: int) -> None:
        """Fence then use the shared real-seq-no/primary-term OCC projection."""
        tenant, environment = document["tenant_id"], document["environment"]
        self.validate_fencing_token(tenant, environment, token)
        self._project(CAPACITY, canonical_id("capacity", tenant, environment, document["resource_id"]), _json(document), tenant, environment, token)

    def get_capacity(self, tenant: str, environment: str, resource_id: str) -> dict[str, Any]:
        try:
            hit = self.es.get(index=CAPACITY, id=canonical_id("capacity", tenant, environment, resource_id))
        except NotFoundError:
            raise KeyError(resource_id) from None
        source = hit["_source"]
        if source.get("tenant_id") != tenant or source.get("environment") != environment:
            raise KeyError(resource_id)
        return source

    def inventory(
        self,
        kind: str,
        tenant: str,
        environment: str,
        *,
        size: int = 50,
        filters: dict[str, Any] | None = None,
        after: list[Any] | None = None,
    ) -> dict[str, Any]:
        indexes = {
            "anomalies": ANOMALIES,
            "forecasts": FORECASTS,
            "failure-candidates": CANDIDATES,
            "signals": SIGNALS,
            "evaluations": EVALUATIONS,
            "capacity": CAPACITY,
        }
        if kind not in indexes:
            raise ValueError("unsupported inventory")
        return self._search(
            indexes[kind],
            tenant,
            environment,
            size=size,
            filters=filters,
            after=after,
            sort=[{"evaluated_at": "desc"}, {"_id": "asc"}],
        )

    def summary_counts(self, tenant: str, environment: str) -> dict[str, int]:
        # Filters remain mandatory even when the backing state is empty.
        result: dict[str, int] = {}
        for state in ("watch", "anomalous", "severe", "recovering", "insufficient_data", "stale"):
            result[state] = self.es.count(
                index=ANOMALIES,
                query={
                    "bool": {
                        "filter": [
                            {"term": {"tenant_id": tenant}},
                            {"term": {"environment": environment}},
                            {"term": {"state": state}},
                        ]
                    }
                },
            )["count"]
        result["failure_candidates"] = self.es.count(
            index=CANDIDATES,
            query={"bool": {"filter": [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]}},
        )["count"]
        return result
