from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from elasticsearch import Elasticsearch

from .checkpoint_store import EventWatermark


class LeaseConflict(RuntimeError):
    pass


class StaleWriter(RuntimeError):
    pass


class ElasticsearchPathwayRepository:
    """Tenant-scoped PIT reader, fenced projection writer, and durable watermark store."""

    def __init__(
        self,
        es: Elasticsearch,
        tenant_id: str,
        environment: str,
        source_streams: list[str],
        *,
        max_documents: int = 2000,
    ):
        self.es, self.tenant_id, self.environment = es, tenant_id, environment
        self.source_streams, self.max_documents = source_streams, max_documents

    @property
    def checkpoint_id(self) -> str:
        digest = hashlib.sha256(",".join(sorted(self.source_streams)).encode()).hexdigest()[:16]
        return f"{self.tenant_id}:{self.environment}:pathway-worker:{digest}"

    def _get(self) -> tuple[dict[str, Any], int | None, int | None]:
        response = self.es.get(index="dataobs-pathway-checkpoints-v1-read", id=self.checkpoint_id, ignore=[404])
        if not response.get("found"):
            return {}, None, None
        return response.get("_source", {}).get("document", {}), response.get("_seq_no"), response.get("_primary_term")

    def checkpoint(self) -> dict[str, Any] | None:
        document, _, _ = self._get()
        return document.get("watermark") if document else None

    def acquire_lease(self, worker_id: str, *, ttl_seconds: int = 60) -> int:
        document, seq, term = self._get()
        now = datetime.now(timezone.utc)
        lease = document.get("lease", {})
        expires = datetime.fromisoformat(lease["expires_at"]) if lease.get("expires_at") else None
        if lease.get("owner_id") != worker_id and expires and expires > now:
            raise LeaseConflict("pathway worker lease is held by another live worker")
        token = int(lease.get("fencing_token", 0)) + (
            lease.get("owner_id") != worker_id or not expires or expires <= now
        )
        updated = document | {
            "lease": {
                "owner_id": worker_id,
                "fencing_token": token,
                "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            }
        }
        kwargs: dict[str, Any] = {
            "index": "dataobs-pathway-checkpoints-v1-write",
            "id": self.checkpoint_id,
            "document": {
                "id": self.checkpoint_id,
                "tenant_id": self.tenant_id,
                "environment": self.environment,
                "document": updated,
            },
            "refresh": "wait_for",
        }
        if seq is not None:
            kwargs |= {"if_seq_no": seq, "if_primary_term": term}
        else:
            kwargs["op_type"] = "create"
        try:
            self.es.index(**kwargs)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409 or "conflict" in str(exc).lower():
                raise LeaseConflict("lease acquisition raced with another worker") from exc
            raise
        return token

    def renew_lease(self, worker_id: str, fencing_token: int, *, ttl_seconds: int = 60) -> None:
        document, seq, term = self._get()
        lease = document.get("lease", {})
        if lease.get("owner_id") != worker_id or lease.get("fencing_token") != fencing_token:
            raise StaleWriter("lease fencing token is stale")
        lease["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        self._replace(document, seq, term)

    def release_lease(self, worker_id: str, fencing_token: int) -> None:
        document, seq, term = self._get()
        lease = document.get("lease", {})
        if lease.get("owner_id") != worker_id or lease.get("fencing_token") != fencing_token:
            raise StaleWriter("lease fencing token is stale")
        lease["expires_at"] = datetime.now(timezone.utc).isoformat()
        lease["owner_id"] = None
        self._replace(document, seq, term)

    def _replace(self, document: dict[str, Any], seq: int | None, term: int | None) -> None:
        kwargs = {
            "index": "dataobs-pathway-checkpoints-v1-write",
            "id": self.checkpoint_id,
            "document": {
                "id": self.checkpoint_id,
                "tenant_id": self.tenant_id,
                "environment": self.environment,
                "document": document,
            },
            "refresh": "wait_for",
            "if_seq_no": seq,
            "if_primary_term": term,
        }
        self.es.index(**kwargs)

    def read_spans(
        self, *, after: list[Any] | None, since: str, size: int = 500
    ) -> tuple[list[dict[str, Any]], list[Any] | None]:
        page_size = min(size, self.max_documents)
        pit = self.es.open_point_in_time(index=",".join(self.source_streams), keep_alive="1m")["id"]
        try:
            request: dict[str, Any] = {
                "pit": {"id": pit, "keep_alive": "1m"},
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"@timestamp": {"gte": since}}},
                            {"term": {"tenant_id": self.tenant_id}},
                            {"term": {"environment": self.environment}},
                        ]
                    }
                },
                "sort": [{"@timestamp": "asc"}, {"_id": "asc"}],
                "size": page_size,
            }
            if after:
                request["search_after"] = after
            response = self.es.search(**request)
            hits = response["hits"]["hits"][: self.max_documents]
            return [hit["_source"] | {"_source_document_id": hit["_id"], "_event_sort": hit["sort"]} for hit in hits], (
                hits[-1]["sort"] if hits else after
            )
        finally:
            self.es.close_point_in_time(id=pit)

    def save(
        self,
        edges: list[dict[str, Any]],
        position: list[Any] | None,
        worker_id: str,
        fencing_token: int,
        documents_processed: int,
        *,
        nodes: list[dict[str, Any]] | None = None,
        pathways: list[dict[str, Any]] | None = None,
    ) -> None:
        document, seq, term = self._get()
        lease = document.get("lease", {})
        if (
            lease.get("owner_id") != worker_id
            or lease.get("fencing_token") != fencing_token
            or datetime.fromisoformat(lease["expires_at"]) <= datetime.now(timezone.utc)
        ):
            raise StaleWriter("projection write rejected by lease fence")
        now = datetime.now(timezone.utc).isoformat()
        base = {"tenant_id": self.tenant_id, "environment": self.environment, "updated_at": now}
        for node in nodes or []:
            self.es.update(
                index="dataobs-pathway-nodes-v1-write",
                id=node["node_id"],
                retry_on_conflict=3,
                doc_as_upsert=True,
                doc=base | node | {"id": node["node_id"]},
            )
        for edge in edges:
            # append-only observation ID makes overlap replay idempotent
            ref = edge.get("source_document_ref", "")
            observation_id = hashlib.sha256(f"{edge['edge_id']}\0{ref}".encode()).hexdigest()
            self.es.index(
                index="logs-dataobs.pathway_event-default",
                id=observation_id,
                op_type="create",
                ignore=[409],
                document=base
                | {
                    "@timestamp": edge.get("last_seen", now),
                    "event_type": "edge_observation",
                    "edge_id": edge["edge_id"],
                    "evidence_ref": ref,
                    "schema_version": "v1",
                },
            )
            self.es.update(
                index="dataobs-pathway-definitions-v1-write",
                id=edge["edge_id"],
                retry_on_conflict=3,
                doc_as_upsert=True,
                doc=base | edge | {"id": edge["edge_id"]},
            )
        for pathway in pathways or []:
            self.es.update(
                index="dataobs-pathway-definitions-v1-write",
                id=pathway["pathway_id"],
                retry_on_conflict=3,
                doc_as_upsert=True,
                doc=base | pathway | {"id": pathway["pathway_id"]},
            )
        watermark = EventWatermark(self.tenant_id, self.environment, **(document.get("watermark") or {}))
        if position:
            watermark = watermark.committed(
                str(position[0]), str(position[1]), documents_processed, worker_id, fencing_token
            )
        document["watermark"] = watermark.document() | {"tenant_id": None, "environment": None}
        document["watermark"].pop("tenant_id")
        document["watermark"].pop("environment")
        document["edges_written"] = int(document.get("edges_written", 0)) + len(edges)
        document["pathways_updated"] = int(document.get("pathways_updated", 0)) + len(pathways or [])
        self._replace(document, seq, term)

    def status(self) -> dict[str, Any]:
        document, _, _ = self._get()
        ok = False
        try:
            ok = bool(self.es.ping())
        except Exception:
            pass
        watermark, lease = document.get("watermark", {}), document.get("lease", {})
        lease_live = bool(
            lease.get("expires_at") and datetime.fromisoformat(lease["expires_at"]) > datetime.now(timezone.utc)
        )
        return {
            "live": True,
            "ready": ok and bool(self.source_streams),
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "worker_id": lease.get("owner_id"),
            "lease_state": "held" if lease_live else "available",
            "checkpoint": watermark,
            "checkpoint_age": None,
            "last_successful_processing": watermark.get("last_successful_processing"),
            "documents_processed": watermark.get("documents_processed", 0),
            "edges_written": document.get("edges_written", 0),
            "pathways_updated": document.get("pathways_updated", 0),
            "consecutive_failures": watermark.get("consecutive_failures", 0),
            "elasticsearch_status": "available" if ok else "unavailable",
            "migration_status": "unknown",
            "source_stream_status": "configured" if self.source_streams else "unavailable",
        }


def replay_start(minutes: int) -> str:
    if not 1 <= minutes <= 31 * 24 * 60:
        raise ValueError("replay range must be between one minute and 31 days")
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
