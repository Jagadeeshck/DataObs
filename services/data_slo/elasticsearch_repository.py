"""Elasticsearch 9 repository with strict server-side scope and OCC."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from elasticsearch import ConflictError, NotFoundError

from packages.domain_model.slo import DataReliabilitySLODefinition, DataReliabilitySLOEvaluation

from .models import DefinitionRevision, RuntimeState
from .repository import DefinitionConflict, FenceLost

DEFINITIONS = "dataobs-slo-definition-current-v1"
REVISIONS = "logs-dataobs.slo-definition-event-default"
EVALUATIONS = "logs-dataobs.slo-evaluation-default"
CURRENT = "dataobs-slo-current-v1"
RUNTIME = "dataobs-slo-runtime-state-v1"


def scoped_id(tenant_id, environment, value):
    return sha256(f"{tenant_id}\0{environment}\0{value}".encode()).hexdigest()


class ElasticsearchDataSLORepository:
    def __init__(self, client):
        self.client = client

    def create_definition(self, value, revision):
        try:
            self.client.create(
                index=DEFINITIONS,
                id=scoped_id(value.tenant_id, value.environment, value.id),
                document=value.model_dump(mode="json"),
                refresh="wait_for",
            )
            self._append_revision(value, revision)
        except ConflictError as exc:
            raise DefinitionConflict("definition already exists") from exc

    def _append_revision(self, value, revision):
        doc = {
            "tenant_id": value.tenant_id,
            "environment": value.environment,
            "slo_id": value.id,
            "revision": revision.revision,
            "actor": revision.actor,
            "reason": revision.reason,
            "recorded_at": revision.recorded_at.isoformat(),
            "definition": revision.definition,
        }
        self.client.create(
            index=REVISIONS,
            id=scoped_id(value.tenant_id, value.environment, f"{value.id}:{revision.revision}"),
            document=doc,
        )

    def get_definition(self, tenant_id, environment, slo_id):
        try:
            hit = self.client.get(index=DEFINITIONS, id=scoped_id(tenant_id, environment, slo_id))
        except NotFoundError:
            return None
        source = hit["_source"]
        if source.get("tenant_id") != tenant_id or source.get("environment") != environment:
            return None
        return DataReliabilitySLODefinition.model_validate(source)

    def list_definitions(self, tenant_id, environment, *, limit, after=None):
        if not 1 <= limit <= 200:
            raise ValueError("bounded limit required")
        body = {
            "index": DEFINITIONS,
            "size": limit,
            "query": {"bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]}},
            "sort": [{"slo_id": "asc"}, {"_id": "asc"}],
        }
        if after:
            body["search_after"] = [after, scoped_id(tenant_id, environment, after)]
        return [
            DataReliabilitySLODefinition.model_validate(h["_source"])
            for h in self.client.search(**body)["hits"]["hits"]
        ]

    def update_definition(self, value, revision, *, expected_etag):
        doc_id = scoped_id(value.tenant_id, value.environment, value.id)
        hit = self.client.get(index=DEFINITIONS, id=doc_id)
        if hit["_source"].get("etag") != expected_etag:
            raise DefinitionConflict("stale ETag")
        try:
            self.client.index(
                index=DEFINITIONS,
                id=doc_id,
                document=value.model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
                refresh="wait_for",
            )
        except ConflictError as exc:
            raise DefinitionConflict("stale ETag") from exc
        self._append_revision(value, revision)

    def list_revisions(self, tenant_id, environment, slo_id, *, limit):
        result = self.client.search(
            index=REVISIONS,
            size=min(limit, 200),
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"slo_id": slo_id}},
                    ]
                }
            },
            sort=[{"revision": "desc"}],
        )
        return [
            DefinitionRevision(
                r["_source"]["slo_id"],
                r["_source"]["revision"],
                r["_source"]["actor"],
                r["_source"]["reason"],
                datetime.fromisoformat(r["_source"]["recorded_at"]),
                r["_source"]["definition"],
            )
            for r in result["hits"]["hits"]
        ]

    def append_evaluation(self, value):
        try:
            self.client.create(
                index=EVALUATIONS,
                id=scoped_id(value.tenant_id, value.environment, value.id),
                document=value.model_dump(mode="json"),
                refresh="wait_for",
            )
            return True
        except ConflictError:
            return False

    def put_current(self, value, *, fencing_token):
        state = self.client.get(index=RUNTIME, id=scoped_id(value.tenant_id, value.environment, value.slo_id))
        if state["_source"]["fencing_token"] != fencing_token:
            raise FenceLost("worker no longer owns fence")
        document = value.model_dump(mode="json") | {
            "evaluation_id": value.id,
            "last_evaluated": value.evaluated_at.isoformat(),
            "schema_version": "v1",
        }
        self.client.index(
            index=CURRENT, id=scoped_id(value.tenant_id, value.environment, value.slo_id), document=document
        )

    def list_due(self, tenant_id, environment, before, *, limit, after=None):
        query = {
            "bool": {
                "filter": [
                    {"term": {"tenant_id": tenant_id}},
                    {"term": {"environment": environment}},
                    {"range": {"next_evaluation_at": {"lte": before.isoformat()}}},
                ]
            }
        }
        args = {
            "index": RUNTIME,
            "size": min(limit, 200),
            "query": query,
            "sort": [{"next_evaluation_at": "asc"}, {"slo_id": "asc"}],
        }
        if after:
            args["search_after"] = [before.isoformat(), after]
        return [RuntimeState(**h["_source"]) for h in self.client.search(**args)["hits"]["hits"]]

    def acquire_lease(self, tenant_id, environment, slo_id, worker_id, now, expires_at):
        """Atomically claim an expired lease and increment its fencing token."""
        script = {
            "source": """if (ctx._source.tenant_id != params.tenant || ctx._source.environment != params.environment) { ctx.op='none'; }
            else if (ctx._source.lease_expires_at != null && ZonedDateTime.parse(ctx._source.lease_expires_at).toInstant().toEpochMilli() > params.now && ctx._source.lease_owner != params.owner) { ctx.op='none'; }
            else { ctx._source.lease_owner=params.owner; ctx._source.lease_expires_at=params.expires; ctx._source.fencing_token=(ctx._source.fencing_token ?: 0)+1; ctx._source.attempt_count=(ctx._source.attempt_count ?: 0)+1; }""",
            "params": {
                "tenant": tenant_id,
                "environment": environment,
                "owner": worker_id,
                "now": int(now.timestamp() * 1000),
                "expires": expires_at.isoformat(),
            },
        }
        result = self.client.update(
            index=RUNTIME, id=scoped_id(tenant_id, environment, slo_id), script=script, refresh="wait_for", _source=True
        )
        return None if result.get("result") == "noop" else result["get"]["_source"]["fencing_token"]

    def get_runtime(self, tenant_id, environment, slo_id):
        hit = self.client.get(index=RUNTIME, id=scoped_id(tenant_id, environment, slo_id))
        source = hit["_source"]
        if source["tenant_id"] != tenant_id or source["environment"] != environment:
            raise KeyError(slo_id)
        return RuntimeState(**source)

    def checkpoint(self, state, *, fencing_token):
        document = {
            key: (value.isoformat() if isinstance(value, datetime) else value) for key, value in state.__dict__.items()
        }
        script = {
            "source": "if (ctx._source.fencing_token != params.fence) { ctx.op='none' } else { ctx._source=params.doc }",
            "params": {"fence": fencing_token, "doc": document},
        }
        result = self.client.update(
            index=RUNTIME,
            id=scoped_id(state.tenant_id, state.environment, state.slo_id),
            script=script,
            refresh="wait_for",
        )
        if result.get("result") == "noop":
            raise FenceLost("worker no longer owns fence")
