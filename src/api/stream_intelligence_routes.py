"""Authenticated Team 1 Stream Intelligence discovery surface."""

from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from packages.streaming.intelligence import CAPABILITIES, METHODS


def create_stream_intelligence_router(require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/stream-intelligence", tags=["stream-intelligence"], dependencies=[Depends(require_auth)]
    )

    @router.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "resource_types": [
                {"resource_type": kind, "metrics": sorted(metrics)} for kind, metrics in CAPABILITIES.items()
            ],
            "detector_methods": sorted(METHODS),
            "directions": ["high", "low", "both"],
            "required_minimum_samples": 3,
            "seasonal_support": ["hour_of_day", "day_of_week_hour"],
            "elastic_ml_required": False,
            "unavailable_capabilities": [
                {"metric": "message_payload_analysis", "reason": "raw payload access is prohibited"}
            ],
        }

    @router.get("/summary")
    def summary(request: Request) -> dict[str, Any]:
        # An empty projection is explicitly unknown/not configured, never normal.
        return {
            "counts": {
                name: 0
                for name in (
                    "watch",
                    "anomalous",
                    "severe",
                    "recovering",
                    "insufficient_data",
                    "stale",
                    "retention_warning",
                    "retention_critical",
                    "exhaustion_predicted",
                    "failure_candidates",
                )
            },
            "data_status": "not_configured",
        }

    @router.get("/runtime")
    def runtime(request: Request) -> dict[str, Any]:
        return {
            "configured": False,
            "lease_status": "unknown",
            "elasticsearch_dependency_state": "unknown",
            "data_status": "not_configured",
        }

    return router
