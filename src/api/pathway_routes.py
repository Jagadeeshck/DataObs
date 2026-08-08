from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from packages.pathways.intelligence import bottlenecks, latency, pathway_health
from packages.pathways.investigation import (
    HistoricalEdge,
    HistoricalNode,
    InvestigationAnchor,
    TraversalRequest,
    WindowMetric,
    compare_metric,
)
from packages.pathways.traversal import traverse
from services.product_query.stream_common import envelope
from services.product_query.stream_investigation import StreamInvestigationRepository
from services.product_query.stream_pagination import CursorCodec, CursorState, InvalidCursor

SAFE_FIELDS = [
    "pathway_id",
    "edge_id",
    "node_id",
    "tenant_id",
    "environment",
    "node_type",
    "name",
    "qualified_name",
    "platform",
    "cluster_id",
    "integration_id",
    "owner_team",
    "business_service",
    "first_seen",
    "last_seen",
    "active",
    "source_node_id",
    "destination_node_id",
    "edge_type",
    "messaging_system",
    "topic_id",
    "consumer_group_id",
    "observation_count",
    "confidence",
    "coverage",
    "health",
    "source_coverage",
    "evidence_refs",
    "schema_version",
    "classification",
    "node_ids",
    "edge_ids",
    "truncated",
    "excluded_edge_count",
    "metrics",
    "reason_codes",
    "edges",
    "nodes",
    "impact_links",
    "warnings",
    "missing_inputs",
    "observed_at",
    "data_status",
    "revision",
    "owner",
    "enabled",
    "metric",
    "objective",
    "evaluation_window",
    "created_at",
    "updated_at",
]


class PathwayRepository:
    def __init__(self, es: Any):
        self.es = getattr(es, "es", es)

    def search(
        self,
        index: str,
        tenant: str,
        environment: str,
        *,
        size: int,
        after: list[Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]
        for field, value in (filters or {}).items():
            if field == "search":
                clauses.append(
                    {
                        "simple_query_string": {
                            "query": value,
                            "fields": ["pathway_id", "name"],
                            "default_operator": "and",
                        }
                    }
                )
            else:
                clauses.append({"term": {field: value}})
        sort_field = "pathway_id" if "definitions" in index else ("node_id" if "nodes" in index else "id")
        body: dict[str, Any] = {
            "index": index,
            "size": size,
            "source": SAFE_FIELDS,
            "query": {"bool": {"filter": clauses}},
            "sort": [{sort_field: "asc"}, {"_id": "asc"}],
        }
        if after:
            body["search_after"] = after
        response = self.es.search(**body)
        return [{"document": hit.get("_source", {}), "sort": hit.get("sort", [])} for hit in response["hits"]["hits"]]

    def get_many(self, index: str, ids: list[str], tenant: str, environment: str) -> list[dict[str, Any]]:
        if not ids:
            return []
        response = self.es.search(
            index=index,
            size=min(len(ids), 200),
            source=SAFE_FIELDS,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {
                            "bool": {
                                "should": [{"terms": {"node_id": ids}}, {"terms": {"edge_id": ids}}],
                                "minimum_should_match": 1,
                            }
                        },
                    ]
                }
            },
            sort=[{"node_id": "asc"}, {"edge_id": "asc"}, {"_id": "asc"}],
        )
        return [hit.get("_source", {}) for hit in response["hits"]["hits"]]

    def get(self, index: str, resource_id: str, tenant: str, environment: str) -> dict[str, Any] | None:
        response = self.es.search(
            index=index,
            size=1,
            source=SAFE_FIELDS,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {
                            "bool": {
                                "should": [
                                    {"term": {"id": resource_id}},
                                    {"term": {"pathway_id": resource_id}},
                                    {"term": {"edge_id": resource_id}},
                                    {"term": {"node_id": resource_id}},
                                ],
                                "minimum_should_match": 1,
                            }
                        },
                    ]
                }
            },
        )
        hits = response["hits"]["hits"]
        return hits[0].get("_source", {}) if hits else None

    def create_slo(self, tenant: str, environment: str, body: dict[str, Any], actor: str) -> dict[str, Any]:
        now, slo_id = datetime.now(timezone.utc).isoformat(), body.get("id") or str(uuid.uuid4())
        clean = {
            key: body.get(key) for key in ("owner", "enabled", "pathway_id", "metric", "objective", "evaluation_window")
        }
        document = clean | {
            "id": slo_id,
            "tenant_id": tenant,
            "environment": environment,
            "revision": 1,
            "created_at": now,
            "created_by": actor,
            "updated_at": now,
            "updated_by": actor,
            "schema_version": "v1",
        }
        self.es.index(
            index="dataobs-pathway-slos-v1-write", id=slo_id, op_type="create", document=document, refresh="wait_for"
        )
        return document

    def update_slo(
        self, slo_id: str, tenant: str, environment: str, body: dict[str, Any], revision: int, actor: str
    ) -> dict[str, Any] | None:
        response = self.es.search(
            index="dataobs-pathway-slos-v1-read",
            size=1,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant}},
                        {"term": {"environment": environment}},
                        {"term": {"id": slo_id}},
                    ]
                }
            },
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        hit, current = hits[0], hits[0]["_source"]
        if current.get("revision") != revision:
            raise ValueError("etag")
        allowed = {
            key: value
            for key, value in body.items()
            if key in {"owner", "enabled", "pathway_id", "metric", "objective", "evaluation_window"}
        }
        updated = (
            current
            | allowed
            | {"revision": revision + 1, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": actor}
        )
        self.es.index(
            index="dataobs-pathway-slos-v1-write",
            id=hit["_id"],
            document=updated,
            if_seq_no=hit["_seq_no"],
            if_primary_term=hit["_primary_term"],
            refresh="wait_for",
        )
        return updated


def create_pathway_router(get_es: Callable[..., Any], require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["pathways"], dependencies=[Depends(require_auth)])
    codec = CursorCodec(os.getenv("DATAOBS_CURSOR_SECRET", "development-cursor-secret-change-me"))

    def repository(es: Any = Depends(get_es)) -> PathwayRepository:
        return PathwayRepository(es)

    def trusted_scope(request: Request) -> tuple[str, str]:
        tenant = getattr(request.state, "tenant_id", None)
        environment = getattr(request.state, "environment", None)
        principal = getattr(request.state, "principal", None)
        if not tenant or not environment or principal is None:
            raise HTTPException(401, detail="Trusted investigation context is required")
        return tenant, environment

    def response_envelope(request: Request, found: bool, sources: list[str] | None = None) -> dict[str, Any]:
        return envelope(request.state.request_id, configured=True, found=found, sources=sources or [])

    async def list_resource(
        index: str,
        route: str,
        request: Request,
        environment: str,
        limit: int,
        cursor: str | None,
        repo: PathwayRepository,
        query_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        filters = {"limit": limit, **(query_filters or {})}
        sort_field = "pathway_id" if "definitions" in index else ("node_id" if "nodes" in index else "id")
        after = None
        if cursor:
            try:
                after = codec.decode(
                    cursor,
                    tenant=request.state.tenant_id,
                    environment=environment,
                    filters=filters,
                    route=route,
                    resource=index,
                    sort={sort_field: "asc"},
                ).sort
            except InvalidCursor as exc:
                raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        hits = repo.search(
            index, request.state.tenant_id, environment, size=limit + 1, after=after, filters=query_filters
        )
        visible, more = hits[:limit], len(hits) > limit
        next_cursor = (
            codec.encode(
                CursorState(visible[-1]["sort"]),
                tenant=request.state.tenant_id,
                environment=environment,
                filters=filters,
                route=route,
                resource=index,
                sort={sort_field: "asc"},
            )
            if visible and more
            else None
        )
        items = [hit["document"] for hit in visible]
        sources = list(dict.fromkeys(source for item in items for source in item.get("source_coverage", [])))
        return {"items": items, "next_cursor": next_cursor, **response_envelope(request, bool(items), sources)}

    @router.get("/pathways")
    async def pathways(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        search: str | None = Query(None, max_length=128),
        health: str | None = Query(None, pattern="^(healthy|degraded|unhealthy|unknown)$"),
        classification: str | None = Query(None, pattern="^(complete|partial)$"),
        owner_team: str | None = Query(None, max_length=128),
        business_service: str | None = Query(None, max_length=128),
        truncated: bool | None = None,
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        return await list_resource(
            "dataobs-pathway-definitions-v1-read",
            "pathways",
            request,
            environment,
            limit,
            cursor,
            repo,
            {
                k: v
                for k, v in {
                    "search": search,
                    "health": health,
                    "classification": classification,
                    "owner_team": owner_team,
                    "business_service": business_service,
                    "truncated": truncated,
                }.items()
                if v is not None
            },
        )

    @router.post("/pathways/search")
    async def pathway_search(
        body: dict[str, Any], request: Request, repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        environment = body.get("environment") or request.state.environment
        return await list_resource(
            "dataobs-pathway-definitions-v1-read",
            "pathway-search",
            request,
            environment,
            min(int(body.get("limit", 50)), 200),
            body.get("cursor"),
            repo,
        )

    @router.get("/pathways/{pathway_id}")
    async def pathway(
        pathway_id: str, request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        item = repo.get("dataobs-pathway-definitions-v1-read", pathway_id, request.state.tenant_id, environment)
        if not item:
            raise HTTPException(404, detail="Pathway not found")
        return item | response_envelope(request, True, item.get("source_coverage", []))

    @router.get("/pathways/{pathway_id}/topology")
    async def topology(
        pathway_id: str, request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        item = await pathway(pathway_id, request, environment, repo)
        nodes = item.get("nodes") or repo.get_many(
            "dataobs-pathway-nodes-v1-read", item.get("node_ids", [])[:200], request.state.tenant_id, environment
        )
        # Durable definitions contain bounded edge evidence. Older projections remain
        # honest (empty) rather than querying the wrong definition resource as edges.
        edges = item.get("edges", [])[:200]
        return {
            "pathway_id": pathway_id,
            "node_ids": item.get("node_ids", []),
            "edge_ids": item.get("edge_ids", []),
            "nodes": nodes,
            "edges": edges,
            **response_envelope(request, True, item.get("source_coverage", [])),
        }

    @router.get("/pathways/{pathway_id}/metrics")
    async def metrics(
        pathway_id: str, request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        item = await pathway(pathway_id, request, environment, repo)
        return {
            "pathway_id": pathway_id,
            "metrics": item.get("metrics", {}),
            **response_envelope(request, bool(item.get("metrics")), item.get("source_coverage", [])),
        }

    @router.get("/pathways/{pathway_id}/latency")
    async def pathway_latency(
        pathway_id: str, request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        item = await pathway(pathway_id, request, environment, repo)
        return {
            "pathway_id": pathway_id,
            **latency(item.get("edges", [])),
            **response_envelope(request, bool(item.get("edges")), item.get("source_coverage", [])),
        }

    @router.get("/pathways/{pathway_id}/bottlenecks")
    async def pathway_bottlenecks(
        pathway_id: str,
        request: Request,
        environment: str = Query(...),
        view: str = Query("latency", pattern="^(latency|reliability|backlog|retention_risk)$"),
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        item = await pathway(pathway_id, request, environment, repo)
        candidates = bottlenecks(item.get("edges", []), view)
        return {
            "items": candidates,
            "root_cause_claimed": False,
            **response_envelope(request, bool(candidates), item.get("source_coverage", [])),
        }

    @router.get("/pathways/{pathway_id}/health")
    async def health(
        pathway_id: str, request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        item = await pathway(pathway_id, request, environment, repo)
        return {
            "pathway_id": pathway_id,
            **pathway_health(item.get("edges", []), partial=item.get("classification") == "partial"),
        }

    @router.get("/pathways/{pathway_id}/impact")
    async def impact(
        pathway_id: str, request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        item = await pathway(pathway_id, request, environment, repo)
        links = [
            link
            for link in item.get("impact_links", [])[:200]
            if link.get("classification") in {"direct", "correlated", "inferred", "unknown"}
        ]
        return {
            "items": links,
            "active_incidents": [x for x in links if x.get("resource_type") == "incident" and x.get("active")],
            **response_envelope(request, bool(links), item.get("source_coverage", [])),
        }

    @router.post("/pathways/{pathway_id}/compare")
    async def compare(
        pathway_id: str,
        body: dict[str, Any],
        request: Request,
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        _, environment = trusted_scope(request)
        if any(key in body for key in ("tenant", "tenant_id", "environment", "actor")):
            raise HTTPException(422, detail="Scope must come from trusted context")
        allowed_dimensions = {"topology", "performance", "reliability", "intelligence", "changes"}
        if not set(body.get("dimensions", [])).issubset(allowed_dimensions):
            raise HTTPException(422, detail="Unknown comparison dimension")
        try:
            baseline, comparison = body["baseline"], body["comparison"]
            windows = [
                (datetime.fromisoformat(value["start"]), datetime.fromisoformat(value["end"]))
                for value in (baseline, comparison)
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, detail="Baseline and comparison windows are required") from exc
        if any(end <= start or end - start > timedelta(days=31) for start, end in windows):
            raise HTTPException(400, detail="Comparison windows must be valid and at most 31 days")
        await pathway(pathway_id, request, environment, repo)
        metrics = []
        for name in sorted(set(baseline.get("metrics", {})) | set(comparison.get("metrics", {}))):
            result = compare_metric(
                WindowMetric(
                    name,
                    baseline.get("metrics", {}).get(name),
                    int(baseline.get("sample_count", 0)),
                    float(baseline.get("coverage", 0)),
                ),
                WindowMetric(
                    name,
                    comparison.get("metrics", {}).get(name),
                    int(comparison.get("sample_count", 0)),
                    float(comparison.get("coverage", 0)),
                ),
            )
            metrics.append(result.__dict__)
        before_edges, after_edges = set(baseline.get("edge_ids", [])), set(comparison.get("edge_ids", []))
        return {
            "pathway_id": pathway_id,
            "metrics": metrics,
            "topology": {
                "edges_added": sorted(after_edges - before_edges),
                "edges_removed": sorted(before_edges - after_edges),
            },
            "causation_claimed": False,
        }

    @router.get("/pathways/{pathway_id}/snapshot")
    async def historical_snapshot(
        pathway_id: str, at: datetime, request: Request, es: Any = Depends(get_es)
    ) -> dict[str, Any]:
        tenant, environment = trusted_scope(request)
        item = StreamInvestigationRepository(es).topology_as_of(tenant, environment, pathway_id, at)
        if item is None:
            return {
                "pathway_id": pathway_id,
                "at": at,
                "data_status": "history_unavailable",
                "topology": None,
                "missing_evidence": ["topology_snapshot"],
                "provenance": "unavailable",
            }
        return {
            "pathway_id": pathway_id,
            "at": at,
            "data_status": "known_active",
            "topology": item,
            "provenance": "observed",
            "missing_evidence": item.get("missing_inputs", []),
        }

    @router.get("/pathways/{pathway_id}/history")
    async def snapshot_history(
        pathway_id: str,
        request: Request,
        start: datetime,
        end: datetime,
        limit: int = Query(50, ge=1, le=100),
        cursor: str | None = None,
        es: Any = Depends(get_es),
    ) -> dict[str, Any]:
        tenant, environment = trusted_scope(request)
        filters = {"pathway_id": pathway_id, "start": start.isoformat(), "end": end.isoformat(), "limit": limit}
        after = None
        if cursor:
            try:
                after = codec.decode(
                    cursor,
                    tenant=tenant,
                    environment=environment,
                    filters=filters,
                    route="pathway-history",
                    resource=pathway_id,
                    sort={"effective_at": "desc", "snapshot_id": "asc"},
                ).sort
            except InvalidCursor as exc:
                raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        try:
            rows = StreamInvestigationRepository(es).topology_between(
                tenant, environment, pathway_id, start, end, limit=limit + 1, after=after
            )
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        visible = rows[:limit]
        next_cursor = (
            codec.encode(
                CursorState(visible[-1]["_sort"]),
                tenant=tenant,
                environment=environment,
                filters=filters,
                route="pathway-history",
                resource=pathway_id,
                sort={"effective_at": "desc", "snapshot_id": "asc"},
            )
            if len(rows) > limit
            else None
        )
        return {
            "items": [{k: v for k, v in row.items() if k != "_sort"} for row in visible],
            "next_cursor": next_cursor,
        }

    @router.post("/pathways/{pathway_id}/blast-radius")
    async def pathway_blast_radius(
        pathway_id: str, body: dict[str, Any], request: Request, repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        tenant, environment = trusted_scope(request)
        if any(key in body for key in ("tenant", "tenant_id", "environment", "actor")):
            raise HTTPException(422, detail="Scope must come from trusted context")
        item = repo.get("dataobs-pathway-definitions-v1-read", pathway_id, tenant, environment)
        if not item:
            raise HTTPException(404, detail="Pathway not found")
        raw_nodes, raw_edges = item.get("nodes", []), item.get("edges", [])
        nodes = [
            HistoricalNode(
                str(n.get("node_id") or n.get("id")),
                str(n.get("node_type", "unknown")),
                str(n.get("name", "")),
                float(n.get("confidence", 1)),
                tuple(n.get("source_coverage", [])),
                tuple(n.get("evidence_refs", [])),
                str(n.get("data_status", "complete")),
            )
            for n in raw_nodes
        ]
        edges = [
            HistoricalEdge(
                str(e.get("edge_id") or e.get("id")),
                str(e["source_node_id"]),
                str(e["destination_node_id"]),
                str(e.get("edge_type", "unknown")),
                e.get("topic"),
                e.get("consumer_group"),
                float(e.get("confidence", 1)),
                tuple(e.get("source_coverage", [])),
                tuple(e.get("evidence_refs", [])),
                str(e.get("data_status", "complete")),
            )
            for e in raw_edges
        ]
        anchor_id = body.get("anchor_node_id") or (nodes[0].node_id if nodes else pathway_id)
        if anchor_id not in {node.node_id for node in nodes}:
            raise HTTPException(422, detail="Anchor is not a member of this pathway")
        try:
            result = traverse(
                nodes,
                edges,
                TraversalRequest(
                    InvestigationAnchor("pathway_node", anchor_id),
                    body.get("direction", "downstream"),
                    int(body.get("max_hops", 5)),
                    min(int(body.get("max_nodes", 100)), 500),
                    min(int(body.get("max_edges", 200)), 1000),
                    min(int(body.get("max_paths", 100)), 500),
                ),
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        return {
            "pathway_id": pathway_id,
            **result.__dict__,
            "paths": [p.__dict__ for p in result.paths],
            "candidates": [c.__dict__ for c in result.candidates],
        }

    @router.get("/pathways/{pathway_id}/investigation-evidence")
    async def investigation_evidence(
        pathway_id: str, request: Request, repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        tenant, environment = trusted_scope(request)
        item = repo.get("dataobs-pathway-definitions-v1-read", pathway_id, tenant, environment)
        if not item:
            raise HTTPException(404, detail="Pathway not found")
        evidence = [
            {
                "event_id": f"pathway:{pathway_id}",
                "event_type": "pathway_observation",
                "effective_at": item.get("observed_at"),
                "observed_at": item.get("observed_at"),
                "resource_type": "pathway",
                "resource_id": pathway_id,
                "severity": item.get("health", "unknown"),
                "summary": "Pathway evidence observed",
                "provenance": "observed",
                "confidence": item.get("confidence", 0),
                "source": "team1_pathways",
                "evidence_ref": (item.get("evidence_refs") or [f"pathway:{pathway_id}"])[0],
            }
        ]
        return {
            "evidence": evidence,
            "related_entities": item.get("impact_links", [])[:50],
            "provider_status": "partial" if item.get("missing_inputs") else "complete",
            "truncated": len(item.get("impact_links", [])) > 50,
            "request_id": request.state.request_id,
        }

    @router.get("/pathways/{pathway_id}/investigation-timeline")
    async def investigation_timeline(
        pathway_id: str,
        request: Request,
        start: datetime,
        end: datetime,
        limit: int = Query(50, ge=1, le=100),
        cursor: str | None = None,
        es: Any = Depends(get_es),
    ) -> dict[str, Any]:
        # Snapshot changes are the initially authoritative Team 1 timeline source.
        page = await snapshot_history(pathway_id, request, start, end, limit, cursor, es)
        items = [
            {
                "event_id": row["snapshot_id"],
                "event_type": "topology_change",
                "effective_at": row["effective_at"],
                "observed_at": row["observed_at"],
                "resource_type": "pathway",
                "resource_id": pathway_id,
                "severity": "info",
                "summary": "Pathway topology snapshot observed",
                "provenance": "observed",
                "confidence": row.get("confidence", 0),
                "source": "pathway_topology_history",
                "evidence_ref": f"snapshot:{row['snapshot_id']}",
            }
            for row in page["items"]
        ]
        return {
            "items": items,
            "next_cursor": page["next_cursor"],
            "partial": True,
            "missing_sources": ["deployment", "incident"],
        }

    @router.post("/stream-investigation/blast-radius")
    async def stream_blast_radius(
        body: dict[str, Any], request: Request, repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        tenant, environment = trusted_scope(request)
        if any(
            key in body for key in ("tenant", "tenant_id", "environment", "actor", "index", "query", "relation_types")
        ):
            raise HTTPException(422, detail="Only bounded traversal fields are accepted")
        anchor_type, anchor_id = body.get("anchor_type"), body.get("anchor_id")
        try:
            anchor = InvestigationAnchor(anchor_type, anchor_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, detail="Invalid anchor") from exc
        if not isinstance(anchor_id, str) or not anchor_id or len(anchor_id) > 512:
            raise HTTPException(422, detail="Invalid anchor")
        node = repo.get("dataobs-pathway-nodes-v1-read", anchor_id, tenant, environment)
        if not node:
            raise HTTPException(404, detail="Anchor not found")
        # Bounded public projection query; no private cross-team indices are accessed.
        hits = repo.search("dataobs-pathway-definitions-v1-read", tenant, environment, size=500)
        edges_raw = [edge for hit in hits for edge in hit["document"].get("edges", [])][:1000]
        ids = sorted(
            {anchor_id}
            | {str(e.get("source_node_id")) for e in edges_raw}
            | {str(e.get("destination_node_id")) for e in edges_raw}
        )[:500]
        nodes_raw = repo.get_many("dataobs-pathway-nodes-v1-read", ids, tenant, environment)
        nodes = [
            HistoricalNode(
                str(n.get("node_id") or n.get("id")),
                str(n.get("node_type", "unknown")),
                str(n.get("name", "")),
                float(n.get("confidence", 1)),
                tuple(n.get("source_coverage", [])),
                tuple(n.get("evidence_refs", [])),
                str(n.get("data_status", "complete")),
            )
            for n in nodes_raw
        ]
        edges = [
            HistoricalEdge(
                str(e.get("edge_id") or e.get("id")),
                str(e["source_node_id"]),
                str(e["destination_node_id"]),
                str(e.get("edge_type", "unknown")),
                e.get("topic"),
                e.get("consumer_group"),
                float(e.get("confidence", 1)),
                tuple(e.get("source_coverage", [])),
                tuple(e.get("evidence_refs", [])),
                str(e.get("data_status", "complete")),
            )
            for e in edges_raw
        ]
        try:
            result = traverse(
                nodes,
                edges,
                TraversalRequest(
                    anchor,
                    body.get("direction", "downstream"),
                    int(body.get("max_hops", 5)),
                    min(int(body.get("max_nodes", 100)), 500),
                    min(int(body.get("max_edges", 200)), 1000),
                    min(int(body.get("max_paths", 100)), 500),
                ),
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        return {
            **result.__dict__,
            "paths": [p.__dict__ for p in result.paths],
            "candidates": [c.__dict__ for c in result.candidates],
        }

    for suffix, index in (
        ("stream-topology/nodes", "dataobs-pathway-nodes-v1-read"),
        ("stream-topology/edges", "dataobs-pathway-definitions-v1-read"),
    ):

        async def listing(
            request: Request,
            environment: str = Query(...),
            limit: int = Query(50, ge=1, le=200),
            cursor: str | None = None,
            repo: PathwayRepository = Depends(repository),
            _suffix: str = suffix,
            _index: str = index,
        ) -> dict[str, Any]:
            return await list_resource(_index, _suffix, request, environment, limit, cursor, repo)

        router.add_api_route(f"/{suffix}", listing, methods=["GET"], name=suffix.replace("/", "_"))

    @router.get("/stream-topology")
    async def stream_topology(
        request: Request, environment: str = Query(...), repo: PathwayRepository = Depends(repository)
    ) -> dict[str, Any]:
        nodes = await list_resource(
            "dataobs-pathway-nodes-v1-read", "topology-nodes", request, environment, 200, None, repo
        )
        edges = await list_resource(
            "dataobs-pathway-definitions-v1-read", "topology-edges", request, environment, 200, None, repo
        )
        return {
            "nodes": nodes["items"],
            "edges": edges["items"],
            **response_envelope(
                request,
                bool(nodes["items"] or edges["items"]),
                list(set(nodes["source_coverage"] + edges["source_coverage"])),
            ),
        }

    @router.post("/pathway-slos", status_code=201)
    async def create_slo(
        body: dict[str, Any],
        request: Request,
        response: Response,
        environment: str = Query(...),
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        metric = body.get("metric")
        objective = body.get("objective")
        window = body.get("evaluation_window")
        if metric not in {"latency", "reliability", "backlog", "retention_risk"}:
            raise HTTPException(422, detail="Unsupported pathway SLO metric")
        if not isinstance(objective, (int, float)) or isinstance(objective, bool) or not 0 < objective <= 100:
            raise HTTPException(422, detail="Objective must be greater than zero and at most 100")
        if not isinstance(window, str) or len(window) > 16 or not window[:-1].isdigit() or window[-1:] not in "mhd":
            raise HTTPException(422, detail="Evaluation window must be a bounded duration such as 15m")
        item = repo.create_slo(request.state.tenant_id, environment, body, str(request.state.principal.subject))
        response.headers["ETag"] = f'"{item["revision"]}"'
        return item

    @router.get("/pathway-slos")
    async def slos(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        pathway_id: str | None = Query(None, max_length=256),
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        return await list_resource(
            "dataobs-pathway-slos-v1-read",
            "pathway-slos",
            request,
            environment,
            limit,
            cursor,
            repo,
            {"pathway_id": pathway_id} if pathway_id else None,
        )

    @router.get("/pathway-slos/{slo_id}")
    async def get_slo(
        slo_id: str,
        request: Request,
        response: Response,
        environment: str = Query(...),
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        item = repo.get("dataobs-pathway-slos-v1-read", slo_id, request.state.tenant_id, environment)
        if not item:
            raise HTTPException(404, detail="Pathway SLO not found")
        response.headers["ETag"] = f'"{item["revision"]}"'
        return item

    @router.patch("/pathway-slos/{slo_id}")
    async def patch_slo(
        slo_id: str,
        body: dict[str, Any],
        request: Request,
        response: Response,
        environment: str = Query(...),
        if_match: str | None = Header(None),
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        try:
            revision = int((if_match or "").strip('"'))
        except ValueError as exc:
            raise HTTPException(412, detail="Valid If-Match revision required") from exc
        try:
            item = repo.update_slo(
                slo_id, request.state.tenant_id, environment, body, revision, str(request.state.principal.subject)
            )
        except ValueError as exc:
            raise HTTPException(412, detail="ETag mismatch") from exc
        if not item:
            raise HTTPException(404, detail="Pathway SLO not found")
        response.headers["ETag"] = f'"{item["revision"]}"'
        return item

    @router.delete("/pathway-slos/{slo_id}", status_code=204)
    async def delete_slo(
        slo_id: str,
        request: Request,
        environment: str = Query(...),
        if_match: str | None = Header(None),
        repo: PathwayRepository = Depends(repository),
    ) -> None:
        item = repo.get("dataobs-pathway-slos-v1-read", slo_id, request.state.tenant_id, environment)
        if not item:
            raise HTTPException(404, detail="Pathway SLO not found")
        if if_match != f'"{item["revision"]}"':
            raise HTTPException(412, detail="ETag mismatch")
        repo.es.delete(index="dataobs-pathway-slos-v1-write", id=slo_id, refresh="wait_for")

    return router
