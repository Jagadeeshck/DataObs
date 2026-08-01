from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from packages.pathways.intelligence import bottlenecks, compare_windows, latency, pathway_health
from services.product_query.stream_common import envelope
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
]


class PathwayRepository:
    def __init__(self, es: Any):
        self.es = getattr(es, "es", es)

    def search(
        self, index: str, tenant: str, environment: str, *, size: int, after: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "index": index,
            "size": size,
            "source": SAFE_FIELDS,
            "query": {"bool": {"filter": [{"term": {"tenant_id": tenant}}, {"term": {"environment": environment}}]}},
            "sort": [{"id": "asc"}, {"_id": "asc"}],
        }
        if after:
            body["search_after"] = after
        response = self.es.search(**body)
        return [{"document": hit.get("_source", {}), "sort": hit.get("sort", [])} for hit in response["hits"]["hits"]]

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
    ) -> dict[str, Any]:
        filters = {"limit": limit}
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
                    sort={"id": "asc"},
                ).sort
            except InvalidCursor as exc:
                raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        hits = repo.search(index, request.state.tenant_id, environment, size=limit + 1, after=after)
        visible, more = hits[:limit], len(hits) > limit
        next_cursor = (
            codec.encode(
                CursorState(visible[-1]["sort"]),
                tenant=request.state.tenant_id,
                environment=environment,
                filters=filters,
                route=route,
                resource=index,
                sort={"id": "asc"},
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
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        return await list_resource(
            "dataobs-pathway-definitions-v1-read", "pathways", request, environment, limit, cursor, repo
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
        return {
            "pathway_id": pathway_id,
            "node_ids": item.get("node_ids", []),
            "edge_ids": item.get("edge_ids", []),
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
        environment: str = Query(...),
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        start, end = datetime.fromisoformat(body["start"]), datetime.fromisoformat(body["end"])
        if end <= start or end - start > timedelta(days=31) or body.get("environment", environment) != environment:
            raise HTTPException(400, detail="Comparison must stay in one environment and within 31 days")
        await pathway(pathway_id, request, environment, repo)
        return {"pathway_id": pathway_id, **compare_windows(body.get("baseline", {}), body.get("comparison", {}))}

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
        item = repo.create_slo(request.state.tenant_id, environment, body, str(request.state.principal.subject))
        response.headers["ETag"] = f'"{item["revision"]}"'
        return item

    @router.get("/pathway-slos")
    async def slos(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repo: PathwayRepository = Depends(repository),
    ) -> dict[str, Any]:
        return await list_resource(
            "dataobs-pathway-slos-v1-read", "pathway-slos", request, environment, limit, cursor, repo
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
