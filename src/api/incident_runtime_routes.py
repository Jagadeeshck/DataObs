from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request


def _envelope(
    request: Request, *, confidence: float | None = None, missing: list[str] | None = None, truncated: bool = False
) -> dict[str, Any]:
    return {
        "data_status": "available",
        "observed_at": None,
        "confidence": confidence,
        "source_coverage": "bounded_projection",
        "missing_inputs": missing or [],
        "warnings": [],
        "truncated": truncated,
        "request_id": request.state.request_id,
    }


def _group(item: Any) -> dict[str, Any]:
    g = item.group
    return {
        "group_id": g.id,
        "representative_incident_id": g.representative_incident_id,
        "member_count": g.total_member_count,
        "member_sample": g.member_incident_ids,
        "members_truncated": g.members_truncated,
        "occurrence_count": g.total_occurrence_count,
        "first_observed_at": g.first_observed_at,
        "last_observed_at": g.last_observed_at,
        "severity": g.highest_severity,
        "confidence": g.confidence,
        "evidence_coverage": g.evidence_coverage,
        "reason_codes": g.reason_codes,
        "policy_version": g.policy_version,
        "policy_name": g.metadata.get("policy_name"),
        "policy_hash": g.metadata.get("policy_hash"),
        "affected_assets": g.metadata.get("affected_assets", []),
        "data_product_ids": g.metadata.get("data_product_ids", []),
        "business_services": g.metadata.get("business_services", []),
        "flood_state": g.flood_state,
        "notification_decision": g.notification_decision,
        "revision": f"{item.seq_no}:{item.primary_term}",
        "wording": "Evidence indicates association; it does not establish causation.",
    }


def _storm(item: Any) -> dict[str, Any]:
    w, p = item.window, item.projection
    events = list(w.events.values())
    first = min((e.occurred_at for e in events), default=None)
    last = max((e.occurred_at for e in events), default=None)
    return {
        "flood_id": w.flood_id,
        "correlation_group_id": w.group_id,
        "state": w.state.value,
        "representative_incident_id": p.get("representative_incident_id"),
        "event_count": len(events),
        "event_rate": p.get("event_rate", 0),
        "incident_count": len({e.incident_id for e in events}),
        "occurrence_count": p.get("total_occurrence_count", len(events)),
        "unique_assets": len({e.asset_id for e in events if e.asset_id}),
        "data_product_ids": sorted({v for e in events for v in e.data_products}),
        "business_services": sorted({v for e in events for v in e.business_services}),
        "first_observed_at": first,
        "last_observed_at": last,
        "suppressed_notification_count": w.suppressed_notification_count,
        "highest_severity": p.get("highest_severity", "medium"),
        "notification_decision": p.get("notification_decision", "notify"),
        "revision": f"{item.seq_no}:{item.primary_term}",
    }


def create_incident_runtime_router(auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(tags=["incident-correlation-runtime"], dependencies=[Depends(auth_dependency)])

    def runtime(request: Request):
        return request.app.state.incident_correlation_coordinator

    @router.get("/api/v1/incident-correlation/groups")
    async def groups(
        request: Request,
        environment: str = Query(min_length=1, max_length=80),
        page_size: int = Query(25, ge=1, le=100),
        coordinator=Depends(runtime),
    ):
        items = coordinator.correlations.list_groups(request.state.tenant_id, environment, limit=page_size)
        return {
            "items": [_group(i) for i in items],
            "next_cursor": None,
            **_envelope(request, truncated=len(items) == page_size),
        }

    @router.get("/api/v1/incident-correlation/groups/{group_id}")
    async def group(group_id: str, request: Request, environment: str, coordinator=Depends(runtime)):
        item = coordinator.correlations.get_group(request.state.tenant_id, environment, group_id)
        if not item:
            raise HTTPException(404, "Correlation group not found")
        return {
            **_group(item),
            **_envelope(request, confidence=item.group.confidence, truncated=item.group.members_truncated),
        }

    @router.get("/api/v1/incident-correlation/groups/{group_id}/members")
    async def members(
        group_id: str,
        request: Request,
        environment: str,
        page_size: int = Query(50, ge=1, le=100),
        coordinator=Depends(runtime),
    ):
        item = coordinator.correlations.get_group(request.state.tenant_id, environment, group_id)
        if not item:
            raise HTTPException(404, "Correlation group not found")
        decisions = coordinator.correlations.list_decisions(request.state.tenant_id, environment, group_id, limit=100)
        ids = sorted({d["incident_id"] for d in decisions if d["action"] in {"create", "attach"}})[:page_size]
        return {
            "items": ids,
            "next_cursor": None,
            **_envelope(request, truncated=item.group.total_member_count > len(ids)),
        }

    @router.get("/api/v1/incident-correlation/groups/{group_id}/decisions")
    async def decisions(
        group_id: str,
        request: Request,
        environment: str,
        page_size: int = Query(50, ge=1, le=100),
        coordinator=Depends(runtime),
    ):
        if not coordinator.correlations.get_group(request.state.tenant_id, environment, group_id):
            raise HTTPException(404, "Correlation group not found")
        return {
            "items": coordinator.correlations.list_decisions(
                request.state.tenant_id, environment, group_id, limit=page_size
            ),
            "next_cursor": None,
            **_envelope(request),
        }

    @router.get("/api/v1/incident-correlation/incidents/{incident_id}")
    async def incident_group(incident_id: str, request: Request, environment: str, coordinator=Depends(runtime)):
        item = coordinator.correlations.find_group_for_incident(request.state.tenant_id, environment, incident_id)
        if not item:
            raise HTTPException(404, "Correlation information not found")
        return {
            **_group(item),
            **_envelope(request, confidence=item.group.confidence, truncated=item.group.members_truncated),
        }

    @router.get("/api/v1/incident-correlation/incidents/{incident_id}/explanation")
    async def explanation(incident_id: str, request: Request, environment: str, coordinator=Depends(runtime)):
        item = coordinator.correlations.find_group_for_incident(request.state.tenant_id, environment, incident_id)
        if not item:
            raise HTTPException(404, "Correlation information not found")
        return {
            "group": _group(item),
            "decisions": coordinator.correlations.list_decisions(
                request.state.tenant_id, environment, item.group.id, limit=100
            ),
            **_envelope(request, confidence=item.group.confidence, truncated=item.group.members_truncated),
        }

    @router.get("/api/v1/incident-floods")
    async def storms(
        request: Request,
        environment: str = Query(min_length=1, max_length=80),
        page_size: int = Query(25, ge=1, le=100),
        coordinator=Depends(runtime),
    ):
        items = coordinator.floods.list_storms(request.state.tenant_id, environment, limit=page_size)
        return {
            "items": [_storm(i) for i in items],
            "next_cursor": None,
            **_envelope(request, truncated=len(items) == page_size),
        }

    @router.get("/api/v1/incident-floods/{flood_id}")
    async def storm(flood_id: str, request: Request, environment: str, coordinator=Depends(runtime)):
        item = coordinator.floods.get_window(request.state.tenant_id, environment, flood_id)
        if not item:
            raise HTTPException(404, "Event storm not found")
        return {**_storm(item), **_envelope(request)}

    @router.get("/api/v1/incident-floods/{flood_id}/members")
    async def storm_members(flood_id: str, request: Request, environment: str, coordinator=Depends(runtime)):
        item = coordinator.floods.get_window(request.state.tenant_id, environment, flood_id)
        if not item:
            raise HTTPException(404, "Event storm not found")
        return {"items": sorted({e.incident_id for e in item.window.events.values()}), **_envelope(request)}

    @router.get("/api/v1/incident-floods/{flood_id}/timeline")
    async def storm_timeline(
        flood_id: str,
        request: Request,
        environment: str,
        page_size: int = Query(50, ge=1, le=100),
        coordinator=Depends(runtime),
    ):
        if not coordinator.floods.get_window(request.state.tenant_id, environment, flood_id):
            raise HTTPException(404, "Event storm not found")
        return {
            "items": coordinator.floods.list_timeline(request.state.tenant_id, environment, flood_id, limit=page_size),
            **_envelope(request),
        }

    @router.get("/api/v1/incident-floods/{flood_id}/notification-decisions")
    async def notifications(flood_id: str, request: Request, environment: str, coordinator=Depends(runtime)):
        if not coordinator.floods.get_window(request.state.tenant_id, environment, flood_id):
            raise HTTPException(404, "Event storm not found")
        timeline = coordinator.floods.list_timeline(request.state.tenant_id, environment, flood_id, limit=100)
        return {"items": [e for e in timeline if e.get("action")], **_envelope(request)}

    return router
