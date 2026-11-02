"""Team 3 internal Watcher webhook.

Elasticsearch Watcher watches registered as an alert source POST their firing
payload to ``POST /internal/watcher/trigger``. This router maps a firing watch
into the existing deduplicating incident pipeline
(:meth:`IncidentManagerService.ingest`), which drives the existing notification
dispatcher. The endpoint sends no notification itself and triggers no
autonomous remediation.

The webhook is authenticated and tenant-scoped like every other route: the
caller's authenticated tenant is authoritative and a payload claiming another
tenant is rejected.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from services.incident_manager import IncidentManagerService
from services.incident_manager.watcher import WatchTriggerError, map_watch_firing_to_event


class WatchFiringBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    watch_id: str = Field(min_length=1, max_length=512)
    asset_id: str | None = Field(default=None, max_length=512)
    monitor_id: str | None = Field(default=None, max_length=512)
    environment: str = Field(default="default", max_length=120)


def create_watcher_router(
    get_incident_manager: Callable[..., IncidentManagerService],
    auth_dependency: Callable[..., Any],
) -> APIRouter:
    router = APIRouter(prefix="/internal/watcher", tags=["watcher"], dependencies=[Depends(auth_dependency)])

    @router.post("/trigger", status_code=202)
    async def trigger(
        body: WatchFiringBody,
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> dict[str, Any]:
        tenant_id = request.state.tenant_id
        try:
            event = map_watch_firing_to_event(body.model_dump(exclude_none=True), tenant_id=tenant_id)
        except WatchTriggerError as exc:
            # A watch reporting "not fired" or a malformed payload is a 422, not
            # a server error: the webhook did its job, there is simply nothing
            # to open.
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            result = manager.ingest(event, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "accepted": True,
            "alert_source": "elasticsearch_watcher",
            "watch_id": body.watch_id,
            "ingestion": result.get("ingestion", {}),
            "incident_id": result.get("incident", {}).get("id"),
        }

    return router
