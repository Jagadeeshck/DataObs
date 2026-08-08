from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from packages.streaming.adapters import ADAPTERS
from services.product_query.stream_common import envelope
from services.product_query.stream_comparison import compare_samples
from services.product_query.stream_pagination import CursorCodec, CursorState, InvalidCursor
from services.product_query.stream_repository import StreamRepository
from services.product_query.stream_sse import EventReplay
from services.stream_observer.repository import MessagingRepository


class CompareRequest(BaseModel):
    mode: Literal[
        "previous_window",
        "selected_window",
        "rolling_baseline",
        "same_period_previous_day",
        "same_period_previous_week",
        "before_after_change",
    ]
    start: datetime
    end: datetime
    baseline_start: datetime | None = None
    baseline_end: datetime | None = None


READ_SCOPE = {
    "streams": "streams:read",
    "stream-clusters": "streams:read",
    "consumer-groups": "streams:read",
    "stream-connectors": "stream-connectors:read",
    "schema-subjects": "stream-schemas:read",
}
RESOURCE = {
    "streams": "streams",
    "stream-clusters": "clusters",
    "consumer-groups": "consumer_groups",
    "stream-connectors": "connectors",
    "schema-subjects": "schemas",
}
SUBRESOURCES = {
    "streams": (
        "partitions",
        "metrics",
        "throughput",
        "latency",
        "applications",
        "consumer-groups",
        "connectors",
        "schemas",
        "configuration",
        "changes",
        "pathways",
        "lineage",
        "incidents",
        "monitors",
        "recommendations",
        "cost",
    ),
    "consumer-groups": (
        "members",
        "assignments",
        "offsets",
        "lag",
        "lag-heatmap",
        "retention-risk",
        "rebalances",
        "applications",
        "incidents",
        "rca",
        "monitors",
    ),
    "stream-connectors": ("tasks", "changes", "incidents", "monitors", "evidence"),
    "schema-subjects": ("versions", "changes", "impact", "incidents", "monitors", "evidence"),
}


def create_stream_router(get_es: Callable[..., Any], require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["stream-360"], dependencies=[Depends(require_auth)])
    codec = CursorCodec(
        os.getenv("DATAOBS_CURSOR_SECRET", "development-cursor-secret-change-me"),
        previous_secrets=[value for value in os.getenv("DATAOBS_CURSOR_PREVIOUS_SECRETS", "").split(",") if value],
    )
    events = EventReplay(int(os.getenv("DATAOBS_STREAM_SSE_REPLAY_SIZE", "500")))

    @router.get("/streams/providers", name="list_stream_providers")
    async def providers(request: Request, es: Any = Depends(get_es)) -> dict[str, Any]:
        """Disclose semantic and collection capability independently per system."""
        scope(request, "streams:read")
        persisted = {
            (state["provider"], state["messaging_system"]): state
            for state in MessagingRepository(es.es).search_runtime_states(
                request.state.tenant_id, request.query_params.get("environment", "production")
            )
        }
        items = []
        for system, adapter_type in ADAPTERS.items():
            capability = adapter_type().capabilities()
            data = capability.model_dump(mode="json")
            state = data.pop("state")
            limitations = data.pop("limitations")
            runtime = persisted.get((data["provider"], system), {})
            items.append(
                {
                    "provider": data.pop("provider"),
                    "messaging_system": system,
                    "configured": runtime.get("configured", state not in {"not_configured", "not_implemented"}),
                    "contract_capability": state,
                    "collection_capability": runtime.get("collection_state", "not_configured"),
                    "runtime_state": runtime.get("projection_state", "not_configured"),
                    "data_freshness": runtime.get("data_status", "not_configured"),
                    "capabilities": data,
                    "limitations": limitations,
                    "latest_observation": runtime.get("last_observation_at"),
                    "source_coverage": runtime.get("source_coverage", 0),
                }
            )
        return {
            "items": items,
            **envelope(request.state.request_id, configured=True, found=True, sources=["capability_registry"]),
        }

    def repo(es: Any = Depends(get_es)) -> StreamRepository:
        return StreamRepository(es.es, timeout=float(os.getenv("DATAOBS_STREAM_QUERY_TIMEOUT", "5")))

    def scope(request: Request, required: str) -> None:
        scopes = set(request.state.principal.get("scopes", []))
        if "dataobs:admin" not in scopes and required not in scopes:
            raise HTTPException(403, detail={"code": "insufficient_scope", "message": f"Required scope: {required}"})

    async def listing(
        root: str,
        request: Request,
        environment: str,
        limit: int,
        cursor: str | None,
        repository: StreamRepository,
        *,
        search: str | None = None,
        health: str | None = None,
        retention_risk: str | None = None,
        cluster_id: str | None = None,
        consumer_group_id: str | None = None,
        sort: str = "topic",
        has_lag: bool | None = None,
    ) -> dict[str, Any]:
        scope(request, READ_SCOPE[root])
        tenant = request.state.tenant_id
        filters = {
            "limit": limit,
            "search": search,
            "health": health,
            "retention_risk": retention_risk,
            "cluster_id": cluster_id,
            "consumer_group_id": consumer_group_id,
            "has_lag": has_lag,
            "sort": sort,
        }
        after = None
        if cursor:
            try:
                after = codec.decode(
                    cursor,
                    tenant=tenant,
                    environment=environment,
                    filters=filters,
                    route=root,
                    resource=RESOURCE[root],
                    sort={"name": sort},
                ).sort
            except InvalidCursor as exc:
                raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        hits = repository.search(
            RESOURCE[root],
            tenant,
            environment,
            size=limit + 1,
            search_after=after,
            search=search,
            health=health,
            retention_risk=retention_risk,
            cluster_id=cluster_id,
            consumer_group_id=consumer_group_id,
            has_lag=has_lag,
            sort=sort,
        )
        # has_lag is intentionally a bounded range filter on the measured maximum lag.
        visible, has_more = hits[:limit], len(hits) > limit
        items = [hit["document"] for hit in visible]
        next_cursor = (
            codec.encode(
                CursorState(visible[-1]["sort"]),
                tenant=tenant,
                environment=environment,
                filters=filters,
                route=root,
                resource=RESOURCE[root],
                sort={"name": sort},
            )
            if visible and has_more
            else None
        )
        return {
            "items": items,
            "next_cursor": next_cursor,
            **envelope(request.state.request_id, configured=True, found=bool(items), sources=["kafka_observer"]),
        }

    for root in RESOURCE:

        async def list_handler(
            request: Request,
            environment: str = Query(..., min_length=1, max_length=64),
            limit: int = Query(50, ge=1, le=200),
            cursor: str | None = None,
            search: str | None = Query(None, max_length=200),
            health: str | None = Query(None, max_length=32),
            retention_risk: str | None = Query(None, max_length=32),
            cluster_id: str | None = Query(None, max_length=256),
            consumer_group_id: str | None = Query(None, max_length=256),
            has_lag: bool | None = None,
            sort: Literal["topic", "last_observed", "maximum_lag", "throughput", "retention_risk", "health"] = "topic",
            repository: StreamRepository = Depends(repo),
            _root: str = root,
        ) -> dict[str, Any]:
            return await listing(
                _root,
                request,
                environment,
                limit,
                cursor,
                repository,
                search=search,
                health=health,
                retention_risk=retention_risk,
                cluster_id=cluster_id,
                consumer_group_id=consumer_group_id,
                has_lag=has_lag,
                sort=sort,
            )

        router.add_api_route(f"/{root}", list_handler, methods=["GET"], name=f"list_{root}")

        async def detail_handler(
            resource_id: str,
            request: Request,
            environment: str = Query(...),
            repository: StreamRepository = Depends(repo),
            _root: str = root,
        ) -> dict[str, Any]:
            scope(request, READ_SCOPE[_root])
            item = repository.get(RESOURCE[_root], resource_id, request.state.tenant_id, environment)
            if item is None:
                raise HTTPException(
                    404,
                    detail={
                        "code": "resource_not_found",
                        "message": "Resource was not found in this tenant and environment",
                    },
                )
            return {
                "item": item,
                **envelope(request.state.request_id, configured=True, found=True, sources=["kafka_observer"]),
            }

        router.add_api_route(f"/{root}/{{resource_id}}", detail_handler, methods=["GET"], name=f"get_{root}")

    for root, names in SUBRESOURCES.items():
        for name in names:

            async def subresource_handler(
                resource_id: str,
                request: Request,
                environment: str = Query(...),
                repository: StreamRepository = Depends(repo),
                _root: str = root,
                _name: str = name,
            ) -> dict[str, Any]:
                scope(request, READ_SCOPE[_root])
                tenant = request.state.tenant_id
                item = repository.get(RESOURCE[_root], resource_id, tenant, environment)
                if item is None:
                    raise HTTPException(
                        404,
                        detail={
                            "code": "resource_not_found",
                            "message": "Resource was not found in this tenant and environment",
                        },
                    )
                methods = {
                    ("stream-connectors", "tasks"): repository.get_connector_tasks,
                    ("stream-connectors", "changes"): repository.get_connector_changes,
                    ("stream-connectors", "incidents"): repository.get_connector_incidents,
                    ("stream-connectors", "monitors"): repository.get_connector_monitors,
                    ("stream-connectors", "evidence"): repository.get_connector_evidence,
                    ("schema-subjects", "versions"): repository.get_schema_versions,
                    ("schema-subjects", "changes"): repository.get_schema_changes,
                    ("schema-subjects", "impact"): repository.get_schema_impact,
                    ("schema-subjects", "incidents"): repository.get_schema_incidents,
                    ("schema-subjects", "monitors"): repository.get_schema_monitors,
                    ("schema-subjects", "evidence"): repository.get_schema_evidence,
                }
                method = methods[(_root, _name)]
                value = method(resource_id, tenant, environment)
                history_sections = {"changes", "incidents", "monitors", "impact"}
                configured = not (_name in history_sections and not item.get(_name.replace("-", "_")))
                status = item.get("data_status") if configured else "not_configured"
                result = {
                    "resource_id": resource_id,
                    "kind": _name,
                    "data": value,
                    **envelope(
                        request.state.request_id,
                        configured=configured,
                        found=value is not None,
                        sources=item.get("source_coverage", []),
                    ),
                }
                result["data_status"] = status or result["data_status"]
                if isinstance(value, list):
                    result.update({"items": value, "next_cursor": None})
                return result

            router.add_api_route(
                f"/{root}/{{resource_id}}/{name}", subresource_handler, methods=["GET"], name=f"get_{root}_{name}"
            )

    cluster_resources = {
        "brokers": ("brokers", "name"),
        "topics": ("streams", "topic"),
        "consumer-groups": ("consumer_groups", "name"),
        "connectors": ("connectors", "name"),
    }

    for section, (related_resource, default_sort) in cluster_resources.items():

        async def cluster_related_handler(
            resource_id: str,
            request: Request,
            environment: str = Query(..., min_length=1, max_length=64),
            limit: int = Query(50, ge=1, le=200),
            cursor: str | None = None,
            search: str | None = Query(None, max_length=200),
            health: str | None = Query(None, max_length=32),
            retention_risk: str | None = Query(None, max_length=32),
            has_lag: bool | None = None,
            sort: str | None = Query(None, max_length=32),
            repository: StreamRepository = Depends(repo),
            _section: str = section,
            _related_resource: str = related_resource,
            _default_sort: str = default_sort,
        ) -> dict[str, Any]:
            scope(request, "streams:read")
            tenant, effective_sort = request.state.tenant_id, sort or _default_sort
            cluster = repository.get("clusters", resource_id, tenant, environment)
            if cluster is None:
                raise HTTPException(
                    404,
                    detail={
                        "code": "resource_not_found",
                        "message": "Cluster was not found in this tenant and environment",
                    },
                )
            filters = {
                "limit": limit,
                "cluster_id": resource_id,
                "search": search,
                "health": health,
                "retention_risk": retention_risk,
                "has_lag": has_lag,
                "sort": effective_sort,
            }
            after = None
            if cursor:
                try:
                    after = codec.decode(
                        cursor,
                        tenant=tenant,
                        environment=environment,
                        filters=filters,
                        route=f"stream-clusters/{_section}",
                        resource=_related_resource,
                        sort={"name": effective_sort},
                    ).sort
                except InvalidCursor as exc:
                    raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
            hits = repository.related(
                _related_resource,
                resource_id,
                tenant,
                environment,
                size=limit + 1,
                search_after=after,
                search=search,
                health=health,
                retention_risk=retention_risk,
                has_lag=has_lag,
                sort=effective_sort,
            )
            visible, has_more = hits[:limit], len(hits) > limit
            items = [hit["document"] for hit in visible]
            next_cursor = (
                codec.encode(
                    CursorState(visible[-1]["sort"]),
                    tenant=tenant,
                    environment=environment,
                    filters=filters,
                    route=f"stream-clusters/{_section}",
                    resource=_related_resource,
                    sort={"name": effective_sort},
                )
                if visible and has_more
                else None
            )
            return {
                "items": items,
                "next_cursor": next_cursor,
                **envelope(request.state.request_id, configured=True, found=bool(items), sources=["kafka_observer"]),
            }

        router.add_api_route(
            f"/stream-clusters/{{resource_id}}/{section}",
            cluster_related_handler,
            methods=["GET"],
            name=f"get_stream_clusters_{section}",
        )

    @router.get("/stream-clusters/{resource_id}/health")
    async def cluster_health(
        resource_id: str, request: Request, environment: str = Query(...), repository: StreamRepository = Depends(repo)
    ) -> dict[str, Any]:
        scope(request, "streams:read")
        cluster = repository.get("clusters", resource_id, request.state.tenant_id, environment)
        if cluster is None:
            raise HTTPException(
                404,
                detail={
                    "code": "resource_not_found",
                    "message": "Cluster was not found in this tenant and environment",
                },
            )
        result = repository.cluster_health(cluster, request.state.tenant_id, environment)
        return {
            **result,
            "warnings": (["Some cluster evidence is missing"] if result["missing_inputs"] else []),
            "request_id": request.state.request_id,
            "next_cursor": None,
        }

    @router.get("/stream-clusters/{resource_id}/changes")
    async def cluster_changes(
        resource_id: str, request: Request, environment: str = Query(...), repository: StreamRepository = Depends(repo)
    ) -> dict[str, Any]:
        scope(request, "streams:read")
        if repository.get("clusters", resource_id, request.state.tenant_id, environment) is None:
            raise HTTPException(
                404,
                detail={
                    "code": "resource_not_found",
                    "message": "Cluster was not found in this tenant and environment",
                },
            )
        return {"items": [], "next_cursor": None, **envelope(request.state.request_id, configured=False, found=False)}

    @router.get("/stream-clusters/{resource_id}/incidents")
    async def cluster_incidents(
        resource_id: str, request: Request, environment: str = Query(...), repository: StreamRepository = Depends(repo)
    ) -> dict[str, Any]:
        scope(request, "streams:read")
        if repository.get("clusters", resource_id, request.state.tenant_id, environment) is None:
            raise HTTPException(
                404,
                detail={
                    "code": "resource_not_found",
                    "message": "Cluster was not found in this tenant and environment",
                },
            )
        return {"items": [], "next_cursor": None, **envelope(request.state.request_id, configured=False, found=False)}

    @router.get("/streams/{resource_id}/inspection-policy")
    async def inspection_policy(resource_id: str, request: Request) -> dict[str, Any]:
        scope(request, "streams:read")
        return {
            "stream_id": resource_id,
            "enabled": False,
            "reason": "Message inspection is disabled by default",
            **envelope(request.state.request_id, configured=False, found=False),
        }

    @router.post("/streams/{resource_id}/inspect", status_code=403)
    async def inspect(resource_id: str, request: Request) -> None:
        scope(request, "streams:inspect")
        raise HTTPException(403, detail={"code": "inspection_disabled", "message": "Message inspection is disabled"})

    for root in ("streams", "stream-clusters", "consumer-groups"):

        async def compare(
            resource_id: str,
            body: CompareRequest,
            request: Request,
            environment: str = Query(...),
            repository: StreamRepository = Depends(repo),
            _root: str = root,
        ) -> dict[str, Any]:
            scope(request, "streams:compare")
            if body.end <= body.start or body.end - body.start > timedelta(days=31):
                raise HTTPException(
                    422,
                    detail={
                        "code": "invalid_time_range",
                        "message": "Comparison range must be positive and at most 31 days",
                    },
                )
            duration = body.end - body.start
            baseline_end = body.baseline_end or body.start
            baseline_start = body.baseline_start or baseline_end - duration
            current = repository.history(
                RESOURCE[_root],
                resource_id,
                request.state.tenant_id,
                environment,
                start=body.start.isoformat(),
                end=body.end.isoformat(),
            )
            baseline = repository.history(
                RESOURCE[_root],
                resource_id,
                request.state.tenant_id,
                environment,
                start=baseline_start.isoformat(),
                end=baseline_end.isoformat(),
            )
            result = compare_samples(current, baseline)
            return {
                "resource_type": _root,
                "resource_id": resource_id,
                "mode": body.mode,
                "comparison_method": "mean_of_observed_samples",
                **result,
                **envelope(
                    request.state.request_id,
                    configured=True,
                    found=result["sample_count"] > 0,
                    sources=["kafka_observer_history"],
                ),
            }

        router.add_api_route(f"/{root}/{{resource_id}}/compare", compare, methods=["POST"], name=f"compare_{root}")

    @router.get("/stream-events")
    async def stream_events(
        request: Request, environment: str = Query(...), last_event_id: int = Header(0, alias="Last-Event-ID")
    ) -> StreamingResponse:
        scope(request, "streams:read")
        tenant = request.state.tenant_id

        async def generate():
            for event in events.replay(tenant, environment, max(0, last_event_id)):
                payload = {"schema_version": 1, "observed_at": event.observed_at, **event.payload}
                yield f"id: {event.event_id}\nevent: {event.event_type}\ndata: {json.dumps(payload)}\n\n"
            yield ": keepalive\n\n"

        return StreamingResponse(
            generate(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
        )

    return router
