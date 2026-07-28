"""Elasticsearch-backed monitor repository.

All resource names are compile-time constants. IDs include a hash of tenant and
environment so identical business IDs cannot collide across scopes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable
from uuid import uuid4

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from packages.domain_model.monitor import (
    MonitorDefinition,
    MonitorEvaluation,
    MonitorFinding,
    MonitorObservation,
    MonitorState,
)
from services.monitoring.repository import ConsistencyError, VersionConflict

MONITORS_ALIAS = "dataobs-monitor-definitions-v2"
DEFINITION_HISTORY_ALIAS = "dataobs-monitor-definition-history-v1"
SCHEDULES = "dataobs-monitor-schedules-v1"
LEASES = "dataobs-monitor-runtime-leases-v1"
CHECKPOINTS = "dataobs-monitor-runtime-checkpoints-v1"
BASELINE_CURRENT = "dataobs-monitor-baselines-v1"
BASELINE_HISTORY = "dataobs-monitor-baseline-history-v1"
EVALUATIONS = "metrics-dataobs.monitor-evaluation-*"
OBSERVATIONS = "metrics-dataobs.monitor-observation-*"
FINDINGS = "logs-dataobs.monitor-finding-*"
SUPPRESSIONS = "dataobs-monitor-suppressions-v1"
RECOMMENDATIONS = "dataobs-monitor-recommendations-v1"
COVERAGE = "dataobs-monitor-coverage-v1"
REQUIRED_RESOURCES = (
    MONITORS_ALIAS,
    DEFINITION_HISTORY_ALIAS,
    SCHEDULES,
    LEASES,
    CHECKPOINTS,
    BASELINE_CURRENT,
    BASELINE_HISTORY,
    SUPPRESSIONS,
    RECOMMENDATIONS,
    COVERAGE,
)


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
            "definition_checksum": sha256(
                json.dumps(self._source(monitor), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "document": self._source(monitor),
        }
        try:
            self.client.create(index=DEFINITION_HISTORY_ALIAS, id=event_id, document=document)
        except ConflictError as exc:
            existing = self.client.get(index=DEFINITION_HISTORY_ALIAS, id=event_id)["_source"]
            comparable = ("tenant_id", "environment", "monitor_id", "revision", "etag", "action", "definition_checksum")
            if all(existing.get(key) == document.get(key) for key in comparable):
                return
            raise ConsistencyError("divergent monitor definition history event") from exc

    def list_monitors(self, tenant_id: str, environment: str, *, limit: int, cursor: str | None = None):
        if cursor is not None:
            raise ValueError("opaque cursor decoding belongs to the API boundary")
        return [
            MonitorDefinition.model_validate(h["_source"])
            for h in self._search(
                MONITORS_ALIAS, tenant_id, environment, limit=limit, sort=[{"updated_at": "desc"}, {"_id": "asc"}]
            )
        ]

    def archive_monitor(self, tenant_id, environment, monitor_id, *, expected_etag):
        current = self.get_monitor(tenant_id, environment, monitor_id)
        if current is None:
            raise KeyError(monitor_id)
        archived = current.model_copy(update={"state": MonitorState.ARCHIVED, "revision": current.revision + 1})
        return self.update_monitor(archived, expected_etag=expected_etag)

    def _search(self, index, tenant_id, environment, *, limit, extra=None, sort=None):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        filters = [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]
        filters.extend(extra or [])
        return self.client.search(
            index=index,
            query={"bool": {"filter": filters}},
            size=limit,
            sort=sort or [{"@timestamp": "desc"}, {"_id": "asc"}],
        )["hits"]["hits"]

    def list_definition_history(self, tenant_id, environment, monitor_id, *, limit):
        return [
            h["_source"]
            for h in self._search(
                DEFINITION_HISTORY_ALIAS,
                tenant_id,
                environment,
                limit=limit,
                extra=[{"term": {"monitor_id": monitor_id}}],
                sort=[{"revision": "desc"}, {"_id": "asc"}],
            )
        ]

    def list_due_schedules(self, tenant_id, environment, before, limit):
        return [
            h["_source"]
            for h in self._search(
                SCHEDULES,
                tenant_id,
                environment,
                limit=limit,
                extra=[{"term": {"state": "enabled"}}, {"range": {"next_scheduled_for": {"lte": before.isoformat()}}}],
                sort=[{"next_scheduled_for": "asc"}, {"_id": "asc"}],
            )
        ]

    def _upsert(self, index, tenant_id, environment, entity_id, document):
        body = {"tenant_id": tenant_id, "environment": environment, **document}
        self.client.index(index=index, id=scoped_id(tenant_id, environment, entity_id), document=body)
        return body

    def save_schedule_state(self, tenant_id, environment, monitor_id, state):
        return self._upsert(SCHEDULES, tenant_id, environment, monitor_id, {"monitor_id": monitor_id, **state})

    def acquire_lease(self, tenant_id, environment, lease_id, owner, now, expires_at):
        doc_id = scoped_id(tenant_id, environment, lease_id)
        script = {
            "source": "if (ctx._source.expires_at != null && ZonedDateTime.parse(ctx._source.expires_at).isAfter(params.now)) { ctx.op='none' } else { ctx._source.owner=params.owner; ctx._source.acquired_at=params.now; ctx._source.renewed_at=params.now; ctx._source.expires_at=params.expires; ctx._source.fencing_token=(ctx._source.fencing_token == null ? 1 : ctx._source.fencing_token + 1); ctx._source.revision=(ctx._source.revision == null ? 1 : ctx._source.revision + 1) }",
            "params": {"owner": owner, "now": now.isoformat(), "expires": expires_at.isoformat()},
        }
        upsert = {
            "tenant_id": tenant_id,
            "environment": environment,
            "lease_id": lease_id,
            "monitor_id": lease_id,
            "owner": owner,
            "acquired_at": now.isoformat(),
            "renewed_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "fencing_token": 1,
            "revision": 1,
        }
        result = self.client.update(index=LEASES, id=doc_id, script=script, upsert=upsert, fetch_source=True)
        return result.get("result") != "noop" and result.get("get", {}).get("_source", {}).get("owner") == owner

    def renew_lease(self, tenant_id, environment, lease_id, owner, expires_at):
        return self._lease_mutation(
            tenant_id,
            environment,
            lease_id,
            owner,
            {"renewed_at": datetime.now(timezone.utc).isoformat(), "expires_at": expires_at.isoformat()},
        )

    def release_lease(self, tenant_id, environment, lease_id, owner):
        return self._lease_mutation(
            tenant_id, environment, lease_id, owner, {"expires_at": datetime.now(timezone.utc).isoformat()}
        )

    def _lease_mutation(self, tenant_id, environment, lease_id, owner, changes):
        doc_id = scoped_id(tenant_id, environment, lease_id)
        try:
            current = self.client.get(index=LEASES, id=doc_id, seq_no_primary_term=True)
        except NotFoundError:
            return False
        if current["_source"].get("owner") != owner:
            return False
        source = {**current["_source"], **changes, "revision": current["_source"].get("revision", 0) + 1}
        try:
            self.client.index(
                index=LEASES,
                id=doc_id,
                document=source,
                if_seq_no=current["_seq_no"],
                if_primary_term=current["_primary_term"],
            )
        except ConflictError:
            return False
        return True

    def append_observation(self, observation):
        key = f"{observation.monitor_id}:{observation.observed_at.isoformat()}"
        try:
            self.client.create(
                index=OBSERVATIONS,
                id=scoped_id(observation.tenant_id, observation.environment, key),
                document=observation.model_dump(mode="json"),
            )
            return True
        except ConflictError:
            return False

    def bulk_observations(self, observations: Iterable[MonitorObservation]):
        return sum(self.append_observation(o) for o in list(observations)[:500])

    def history(self, tenant_id, environment, monitor_id, before, limit):
        return [
            MonitorObservation.model_validate(h["_source"])
            for h in self._search(
                OBSERVATIONS,
                tenant_id,
                environment,
                limit=limit,
                extra=[{"term": {"monitor_id": monitor_id}}, {"range": {"observed_at": {"lt": before.isoformat()}}}],
                sort=[{"observed_at": "asc"}, {"_id": "asc"}],
            )
        ]

    def create_baseline_version(self, baseline):
        key = baseline["baseline_version"]
        try:
            self.client.create(
                index=BASELINE_HISTORY,
                id=scoped_id(baseline["tenant_id"], baseline["environment"], key),
                document=baseline,
            )
        except ConflictError:
            existing = self.client.get(
                index=BASELINE_HISTORY, id=scoped_id(baseline["tenant_id"], baseline["environment"], key)
            )["_source"]
            if existing != baseline:
                raise ConsistencyError("divergent baseline version")
            return False
        self._upsert(BASELINE_CURRENT, baseline["tenant_id"], baseline["environment"], baseline["monitor_id"], baseline)
        return True

    def get_current_baseline(self, tenant_id, environment, monitor_id):
        return self._get_dict(BASELINE_CURRENT, tenant_id, environment, monitor_id)

    def list_baseline_versions(self, tenant_id, environment, monitor_id, *, limit):
        return [
            h["_source"]
            for h in self._search(
                BASELINE_HISTORY,
                tenant_id,
                environment,
                limit=limit,
                extra=[{"term": {"monitor_id": monitor_id}}],
                sort=[{"created_at": "desc"}, {"_id": "asc"}],
            )
        ]

    def reset_baseline(self, tenant_id, environment, monitor_id, *, actor, reason):
        if not actor or not reason:
            raise ValueError("actor and reason are required")
        return self._upsert(
            BASELINE_CURRENT,
            tenant_id,
            environment,
            monitor_id,
            {
                "monitor_id": monitor_id,
                "cold_start_state": "reset_required",
                "reset_reason": reason,
                "reset_actor": actor,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _create_model(self, index, key, model):
        document = model.model_dump(mode="json")
        try:
            self.client.create(
                index=index, id=scoped_id(document["tenant_id"], document["environment"], key), document=document
            )
            return True
        except ConflictError:
            existing = self.client.get(index=index, id=scoped_id(document["tenant_id"], document["environment"], key))[
                "_source"
            ]
            if existing != document:
                raise ConsistencyError("idempotency key reused with different payload")
            return False

    def save_evaluation(self, evaluation, *, idempotency_key):
        return self._create_model(EVALUATIONS, idempotency_key, evaluation)

    def get_evaluation(self, tenant_id, environment, evaluation_id):
        value = self._get_dict(EVALUATIONS, tenant_id, environment, evaluation_id)
        return MonitorEvaluation.model_validate(value) if value else None

    def list_evaluations(self, tenant_id, environment, monitor_id, *, limit):
        return [
            MonitorEvaluation.model_validate(h["_source"])
            for h in self._search(
                EVALUATIONS,
                tenant_id,
                environment,
                limit=limit,
                extra=[{"term": {"monitor_id": monitor_id}}],
                sort=[{"evaluated_at": "desc"}, {"_id": "asc"}],
            )
        ]

    def save_finding(self, finding, *, idempotency_key):
        return self._create_model(FINDINGS, idempotency_key, finding)

    def list_findings(self, tenant_id, environment, monitor_id, *, limit):
        return [
            MonitorFinding.model_validate(hit["_source"])
            for hit in self._search(
                FINDINGS,
                tenant_id,
                environment,
                limit=limit,
                extra=[{"term": {"monitor_id": monitor_id}}],
                sort=[{"finding_id": "asc"}],
            )
        ]

    def request_execution(self, tenant_id, environment, monitor_id, *, scheduled_for, idempotency_key=None):
        token = idempotency_key or str(uuid4())
        if len(token) > 200:
            raise ValueError("idempotency key is too long")
        execution_id = sha256(f"{tenant_id}\0{environment}\0{monitor_id}\0{token}".encode()).hexdigest()
        existing = self._get_dict(SCHEDULES, tenant_id, environment, monitor_id) or {}
        document = {
            **existing,
            "monitor_id": monitor_id,
            "state": "enabled",
            "next_scheduled_for": scheduled_for.isoformat(),
            "execution_id": execution_id,
            "execution_request": True,
            "idempotency_key_hash": sha256(token.encode()).hexdigest(),
        }
        if existing and existing.get("execution_id") == execution_id:
            return execution_id
        self._upsert(SCHEDULES, tenant_id, environment, monitor_id, document)
        return execution_id

    def create_suppression(self, suppression):
        return self._upsert(
            SUPPRESSIONS, suppression["tenant_id"], suppression["environment"], suppression["id"], suppression
        )

    def get_active_suppressions(self, tenant_id, environment, monitor_id, at):
        return [
            h["_source"]
            for h in self._search(
                SUPPRESSIONS,
                tenant_id,
                environment,
                limit=100,
                extra=[
                    {"term": {"monitor_id": monitor_id}},
                    {"range": {"starts_at": {"lte": at.isoformat()}}},
                    {"range": {"ends_at": {"gt": at.isoformat()}}},
                ],
            )
        ]

    def end_suppression(self, tenant_id, environment, suppression_id, *, actor):
        value = self._get_dict(SUPPRESSIONS, tenant_id, environment, suppression_id)
        if value is None:
            raise KeyError(suppression_id)
        return self._upsert(
            SUPPRESSIONS,
            tenant_id,
            environment,
            suppression_id,
            {**value, "state": "ended", "ended_by": actor, "ends_at": datetime.now(timezone.utc).isoformat()},
        )

    def create_recommendation(self, recommendation):
        return self._upsert(
            RECOMMENDATIONS,
            recommendation["tenant_id"],
            recommendation["environment"],
            recommendation["id"],
            recommendation,
        )

    def get_recommendation(self, tenant_id, environment, recommendation_id):
        return self._get_dict(RECOMMENDATIONS, tenant_id, environment, recommendation_id)

    def list_recommendations(self, tenant_id, environment, *, limit):
        return [
            h["_source"]
            for h in self._search(
                RECOMMENDATIONS, tenant_id, environment, limit=limit, sort=[{"updated_at": "desc"}, {"_id": "asc"}]
            )
        ]

    def transition_recommendation(self, tenant_id, environment, recommendation_id, state, *, actor):
        if state not in {"accepted", "rejected", "deferred", "expired", "superseded"}:
            raise ValueError("invalid recommendation transition")
        value = self.get_recommendation(tenant_id, environment, recommendation_id)
        if value is None:
            raise KeyError(recommendation_id)
        return self._upsert(
            RECOMMENDATIONS,
            tenant_id,
            environment,
            recommendation_id,
            {**value, "state": state, "transition_actor": actor, "updated_at": datetime.now(timezone.utc).isoformat()},
        )

    def save_coverage(self, tenant_id, environment, coverage):
        self._upsert(COVERAGE, tenant_id, environment, coverage.get("scope_id", "default"), coverage)

    def get_coverage(self, tenant_id, environment):
        hits = self._search(COVERAGE, tenant_id, environment, limit=1)
        return hits[0]["_source"] if hits else None

    def _get_dict(self, index, tenant_id, environment, entity_id):
        try:
            value = self.client.get(index=index, id=scoped_id(tenant_id, environment, entity_id))["_source"]
        except NotFoundError:
            return None
        return value if value.get("tenant_id") == tenant_id and value.get("environment") == environment else None

    def get_checkpoint(self, tenant_id, environment, monitor_id):
        return self._get_dict(CHECKPOINTS, tenant_id, environment, monitor_id)

    def checkpoint(self, tenant_id, environment, monitor_id, value, *, expected_revision):
        current = self.get_checkpoint(tenant_id, environment, monitor_id)
        revision = (current or {}).get("revision", 0)
        if expected_revision is not None and expected_revision != revision:
            raise VersionConflict("stale checkpoint revision")
        self._upsert(
            CHECKPOINTS,
            tenant_id,
            environment,
            monitor_id,
            {"monitor_id": monitor_id, **value, "revision": revision + 1},
        )
        return revision + 1

    def readiness(self):
        missing = [name for name in REQUIRED_RESOURCES if not self.client.indices.exists(index=name)]
        if missing:
            raise RuntimeError("missing monitor runtime resources: " + ", ".join(missing))
        return {"ready": True, "migration": "0013_monitor_runtime_completion"}
