"""Typed monitoring API. Development authentication is not production authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from packages.domain_model.monitor import MonitorDefinition, MonitorState
from services.monitoring.capabilities import capability_documents, validate_monitor_definition
from services.monitoring.repository import ConsistencyError, VersionConflict
from services.monitoring.staleness import monitor_staleness

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


class MonitorPage(BaseModel):
    items: list[MonitorDefinition]
    next_cursor: str | None = None


def evidence(request: Request, status: str = "complete", *, warnings=None, missing=None, coverage=None):
    return {
        "data_status": status,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_coverage": coverage or ["monitor_definitions"],
        "confidence": 1.0 if status == "complete" else 0.5,
        "warnings": warnings or [],
        "missing_inputs": missing or [],
        "request_id": getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid4()),
    }


def _cursor_secret() -> bytes:
    return os.getenv("DATAOBS_CURSOR_SECRET", "dataobs-development-cursor-secret").encode()


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(_cursor_secret(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + signature).decode().rstrip("=")


def decode_cursor(value: str, expected: dict[str, Any]) -> dict[str, Any]:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        raw, signature = decoded[:-32], decoded[-32:]
        if not hmac.compare_digest(signature, hmac.new(_cursor_secret(), raw, hashlib.sha256).digest()):
            raise ValueError
        payload = json.loads(raw)
        if any(payload.get(key) != item for key, item in expected.items()):
            raise ValueError
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "invalid or mismatched cursor") from exc


def require_monitor(request: Request, monitor_id: str):
    value = repo(request).get_monitor(*scope(request), monitor_id)
    if value is None:
        raise HTTPException(404, "monitor not found")
    return value


def target_display(monitor: MonitorDefinition) -> str:
    target = monitor.target
    return next(
        (
            value
            for value in (
                target.field_id,
                target.asset_id,
                target.pathway_id,
                target.pipeline_id,
                target.service_id,
                target.table_name,
            )
            if value
        ),
        monitor.id,
    )


def monitor_summary(monitor: MonitorDefinition) -> dict[str, Any]:
    stale = monitor_staleness(state=monitor.state, interval=monitor.schedule.interval, last_observation_at=None)
    return {
        "id": monitor.id,
        "name": monitor.name,
        "monitor_type": monitor.monitor_type.value,
        "state": monitor.state.value,
        "target_type": monitor.target.source_type,
        "target_display_name": target_display(monitor),
        "managed_by": monitor.managed_by,
        "creation_source": monitor.creation_source,
        "schedule_interval": monitor.schedule.interval,
        "threshold_mode": monitor.threshold.mode.value,
        "severity": monitor.alert.severity,
        "last_observation_at": None,
        "last_value": None,
        "unit": None,
        "last_evaluation_at": None,
        "last_evaluation_status": None,
        "anomaly_score": None,
        "confidence": stale.confidence,
        "open_finding_count": None,
        "highest_open_severity": None,
        "incident_count": None,
        "cold_start_state": None,
        "stale": stale.stale,
        "updated_at": monitor.updated_at,
        "revision": monitor.revision,
    }


class MonitorPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: MonitorState | None = None
    etag: str


class SuppressionRequest(BaseModel):
    starts_at: str
    ends_at: str
    reason: str = Field(min_length=1, max_length=500)
    approval_reference: str = Field(min_length=1, max_length=200)


class TransitionRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)


class RunRequest(BaseModel):
    scheduled_for: datetime | None = None


def repo(request: Request):
    value = getattr(request.app.state, "monitor_repository", None)
    if value is None:
        raise HTTPException(503, "monitor runtime repository unavailable")
    return value


def scope(request):
    return request.state.tenant_id, getattr(request.app.state.settings, "environment", "default")


def translate(exc):
    if isinstance(exc, VersionConflict):
        raise HTTPException(412, "monitor changed concurrently")
    if isinstance(exc, ConsistencyError):
        raise HTTPException(409, "immutable monitor history diverged")
    raise exc


@router.get("/quality/capabilities")
def capabilities():
    return {"schema_version": "v1", "items": capability_documents()}


@router.get("/quality/monitors")
@router.get("/monitors", response_model=MonitorPage, deprecated=True)
def list_monitors(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    search: str | None = Query(None, max_length=200),
    state: str | None = None,
    monitor_type: str | None = None,
    threshold_mode: str | None = None,
    managed_by: str | None = None,
    creation_source: str | None = None,
    asset_id: str | None = None,
    field_id: str | None = None,
    source_type: str | None = None,
    has_open_findings: bool | None = None,
    has_incident: bool | None = None,
    is_stale: bool | None = None,
    sort: Literal[
        "name",
        "last_updated",
        "state",
        "monitor_type",
        "last_observation",
        "last_evaluation",
        "open_findings",
        "severity",
    ] = "last_updated",
):
    tenant, environment = scope(request)
    filters = {
        k: v
        for k, v in locals().copy().items()
        if k
        in {
            "search",
            "state",
            "monitor_type",
            "threshold_mode",
            "managed_by",
            "creation_source",
            "asset_id",
            "field_id",
            "source_type",
            "has_open_findings",
            "has_incident",
            "is_stale",
        }
        and v is not None
    }
    binding = {
        "tenant": tenant,
        "environment": environment,
        "route": "quality-monitors",
        "filters": filters,
        "sort": sort,
    }
    offset = int(decode_cursor(cursor, binding)["offset"]) if cursor else 0
    # The compatibility repository contract is bounded; richer Elasticsearch implementations may push these filters down.
    monitors = list(repo(request).list_monitors(tenant, environment, limit=200, cursor=None))

    def matches(m):
        if search and search.casefold() not in f"{m.name} {target_display(m)}".casefold():
            return False
        exact = {
            "state": m.state.value,
            "monitor_type": m.monitor_type.value,
            "threshold_mode": m.threshold.mode.value,
            "managed_by": m.managed_by,
            "creation_source": m.creation_source,
            "asset_id": m.target.asset_id,
            "field_id": m.target.field_id,
            "source_type": m.target.source_type,
        }
        return all(exact.get(key) == value for key, value in filters.items() if key in exact)

    rows = [monitor_summary(m) for m in monitors if matches(m)]
    sort_keys = {
        "name": "name",
        "state": "state",
        "monitor_type": "monitor_type",
        "severity": "severity",
        "last_updated": "updated_at",
    }
    key = sort_keys.get(sort, "updated_at")
    rows.sort(key=lambda row: (str(row.get(key) or ""), row["id"]), reverse=sort == "last_updated")
    if is_stale is not None:
        rows = [row for row in rows if row["stale"] is is_stale]
    if has_open_findings is not None:
        rows = [
            row
            for row in rows
            if row["open_finding_count"] is not None and (row["open_finding_count"] > 0) is has_open_findings
        ]
    if has_incident is not None:
        rows = [
            row for row in rows if row["incident_count"] is not None and (row["incident_count"] > 0) is has_incident
        ]
    page = rows[offset : offset + limit]
    next_cursor = encode_cursor({**binding, "offset": offset + limit}) if offset + limit < len(rows) else None
    return {
        "items": page,
        "next_cursor": next_cursor,
        **evidence(
            request,
            "partial",
            warnings=["Operational summaries are unavailable in the definition read model"],
            missing=["observations", "evaluations", "findings"],
        ),
    }


@router.post("/quality/monitors", response_model=MonitorDefinition, status_code=201)
@router.post("/monitors", response_model=MonitorDefinition, status_code=201, deprecated=True)
def create_monitor(body: MonitorDefinition, request: Request, response: Response):
    tenant, environment = scope(request)
    if (body.tenant_id, body.environment) != (tenant, environment):
        raise HTTPException(403, "tenant or environment override is forbidden")
    try:
        validate_monitor_definition(body)
        value = repo(request).create_monitor(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        translate(exc)
    response.headers["ETag"] = value.etag
    return value


@router.get("/quality/monitors/{monitor_id}")
@router.get("/monitors/{monitor_id}", response_model=MonitorDefinition, deprecated=True)
def get_monitor(monitor_id: str, request: Request, response: Response):
    value = repo(request).get_monitor(*scope(request), monitor_id)
    if value is None:
        raise HTTPException(404, "monitor not found")
    response.headers["ETag"] = value.etag
    definition = value.model_dump(mode="json")
    return {
        **definition,
        **monitor_summary(value),
        "monitor_version": value.monitor_version,
        "threshold": definition["threshold"],
        "baseline": definition.get("baseline"),
        "alert": definition["alert"],
        "target": definition["target"],
        "last_observation": None,
        "last_evaluation": None,
        "current_baseline": None,
        "active_suppression_count": None,
        "health": "unknown",
        "reason_codes": ["operational_evidence_missing"],
        **evidence(
            request,
            "partial",
            warnings=["Operational evidence is not present in the definition read model"],
            missing=["observations", "evaluations", "findings"],
        ),
    }


@router.patch("/quality/monitors/{monitor_id}", response_model=MonitorDefinition)
@router.patch("/monitors/{monitor_id}", response_model=MonitorDefinition, deprecated=True)
def patch_monitor(monitor_id: str, body: MonitorPatch, request: Request, if_match: str | None = Header(None)):
    if not if_match:
        raise HTTPException(428, "If-Match is required")
    value = repo(request).get_monitor(*scope(request), monitor_id)
    if value is None:
        raise HTTPException(404, "monitor not found")
    updated = value.model_copy(
        update={"state": body.state or value.state, "etag": body.etag, "revision": value.revision + 1}
    )
    try:
        return repo(request).update_monitor(updated, expected_etag=if_match)
    except Exception as exc:
        translate(exc)


def state_route(state):
    def transition(monitor_id: str, request: Request, if_match: str | None = Header(None)):
        if not if_match:
            raise HTTPException(428, "If-Match is required")
        value = repo(request).get_monitor(*scope(request), monitor_id)
        if value is None:
            raise HTTPException(404, "monitor not found")
        return repo(request).update_monitor(
            value.model_copy(update={"state": state, "revision": value.revision + 1}), expected_etag=if_match
        )

    return transition


for prefix in ("/monitors", "/quality/monitors"):
    router.add_api_route(f"{prefix}/{{monitor_id}}/enable", state_route(MonitorState.ENABLED), methods=["POST"])
    router.add_api_route(f"{prefix}/{{monitor_id}}/disable", state_route(MonitorState.DISABLED), methods=["POST"])


@router.post("/quality/monitors/{monitor_id}/archive")
@router.delete("/quality/monitors/{monitor_id}")
@router.post("/monitors/{monitor_id}/archive", deprecated=True)
def archive(monitor_id: str, request: Request, if_match: str | None = Header(None)):
    if not if_match:
        raise HTTPException(428, "If-Match is required")
    return repo(request).archive_monitor(*scope(request), monitor_id, expected_etag=if_match)


@router.get("/quality/monitors/{monitor_id}/history")
@router.get("/monitors/{monitor_id}/history", deprecated=True)
def history(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    require_monitor(request, monitor_id)
    items = repo(request).list_definition_history(*scope(request), monitor_id, limit=limit)
    safe = [
        {key: item.get(key) for key in ("revision", "action", "actor", "etag", "definition_checksum", "occurred_at")}
        for item in items
    ]
    return {"items": safe, "next_cursor": None, **evidence(request)}


@router.get("/quality/monitors/{monitor_id}/observations")
@router.get("/monitors/{monitor_id}/observations", deprecated=True)
def observations(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    from datetime import datetime, timezone

    require_monitor(request, monitor_id)
    items = repo(request).history(*scope(request), monitor_id, datetime.now(timezone.utc), limit)
    return {"items": items, "next_cursor": None, **evidence(request, coverage=["monitor_observations"])}


@router.get("/quality/monitors/{monitor_id}/baselines")
@router.get("/monitors/{monitor_id}/baselines", deprecated=True)
def baselines(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    require_monitor(request, monitor_id)
    return {
        "items": repo(request).list_baseline_versions(*scope(request), monitor_id, limit=limit),
        "next_cursor": None,
        **evidence(request, coverage=["monitor_baselines"]),
    }


@router.post("/quality/monitors/{monitor_id}/baselines/reset")
@router.post("/monitors/{monitor_id}/baselines/reset", deprecated=True)
def reset_baseline(
    monitor_id: str, body: TransitionRequest, request: Request, reason: str = Query(..., min_length=1, max_length=500)
):
    return repo(request).reset_baseline(*scope(request), monitor_id, actor=body.actor, reason=reason)


@router.get("/quality/monitors/{monitor_id}/evaluations")
@router.get("/monitors/{monitor_id}/evaluations", deprecated=True)
def evaluations(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    require_monitor(request, monitor_id)
    values = repo(request).list_evaluations(*scope(request), monitor_id, limit=limit)
    items = []
    for value in values:
        item = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
        observation = item.pop("observation", {})
        item["actual_value"] = observation.get("value")
        item["unit"] = observation.get("unit")
        items.append(item)
    return {"items": items, "next_cursor": None, **evidence(request, coverage=["monitor_evaluations"])}


@router.get("/quality/monitors/{monitor_id}/findings")
@router.get("/monitors/{monitor_id}/findings", deprecated=True)
def findings(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    require_monitor(request, monitor_id)
    values = repo(request).list_findings(*scope(request), monitor_id, limit=limit)
    items = []
    for value in values:
        item = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
        item.update(
            {
                "opened_at": item.get("opened_at"),
                "updated_at": item.get("updated_at"),
                "recovered_at": item.get("recovered_at"),
                "relationship": "direct" if item.get("incident_id") else "unknown",
            }
        )
        items.append(item)
    return {"items": items, "next_cursor": None, **evidence(request, coverage=["monitor_findings"])}


@router.get("/quality/monitors/{monitor_id}/incidents")
def incidents(monitor_id: str, request: Request):
    require_monitor(request, monitor_id)
    findings = repo(request).list_findings(*scope(request), monitor_id, limit=100)
    return {
        "items": [
            {
                "incident_id": finding.incident_id,
                "finding_id": finding.finding_id,
                "relationship": "direct",
                "state": finding.state,
                "severity": finding.severity,
                "observed_at": None,
            }
            for finding in findings
            if finding.incident_id
        ],
        "next_cursor": None,
        **evidence(request, coverage=["monitor_findings"]),
    }


@router.get("/quality/monitors/{monitor_id}/suppressions")
@router.get("/monitors/{monitor_id}/suppressions", deprecated=True)
def suppressions(monitor_id: str, request: Request):
    from datetime import datetime, timezone

    require_monitor(request, monitor_id)
    return {
        "items": repo(request).get_active_suppressions(*scope(request), monitor_id, datetime.now(timezone.utc)),
        "next_cursor": None,
        **evidence(request, coverage=["monitor_suppressions"]),
    }


@router.post("/quality/monitors/{monitor_id}/suppressions", status_code=201)
def create_suppression(monitor_id: str, body: SuppressionRequest, request: Request):
    tenant, environment = scope(request)
    starts_at, ends_at = datetime.fromisoformat(body.starts_at), datetime.fromisoformat(body.ends_at)
    if ends_at <= starts_at or (ends_at - starts_at).days > 31:
        raise HTTPException(422, "suppression must have a positive duration of at most 31 days")
    principal = request.state.principal
    return repo(request).create_suppression(
        {
            "id": str(uuid4()),
            "monitor_id": monitor_id,
            "tenant_id": tenant,
            "environment": environment,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "reason": body.reason,
            "approved_by": body.approval_reference,
            "created_by": principal.subject,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "revision": 1,
            "state": "active",
        }
    )


@router.post("/quality/monitors/{monitor_id}/run", status_code=202)
def run_monitor(
    monitor_id: str,
    body: RunRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    tenant, environment = scope(request)
    monitor = repo(request).get_monitor(tenant, environment, monitor_id)
    if monitor is None:
        raise HTTPException(404, "monitor not found")
    if monitor.state not in {MonitorState.ENABLED, MonitorState.ACTIVE, MonitorState.LEARNING}:
        raise HTTPException(409, "only enabled monitors can be run")
    execution_id = repo(request).request_execution(
        tenant,
        environment,
        monitor_id,
        scheduled_for=body.scheduled_for or datetime.now(timezone.utc),
        idempotency_key=idempotency_key,
    )
    return {"execution_id": execution_id, "status": "queued"}


@router.get("/quality/overview")
def quality_overview(request: Request):
    """Bounded definition summary; unavailable evidence remains explicitly unknown."""
    monitors = list(repo(request).list_monitors(*scope(request), limit=200, cursor=None))
    counts = {state.value: 0 for state in MonitorState}
    for monitor in monitors:
        counts[monitor.state.value] += 1
    runtime = getattr(request.app.state, "monitor_runtime_health", None)
    runtime_snapshot = runtime.snapshot() if runtime is not None else None
    coverage_value = repo(request).get_coverage(*scope(request))
    coverage_value = coverage_value.model_dump(mode="json") if hasattr(coverage_value, "model_dump") else coverage_value
    denominator = coverage_value.get("denominator") if coverage_value else None
    numerator = coverage_value.get("numerator") if coverage_value else None
    missing = ["finding_aggregation", "observation_aggregation", "evaluation_aggregation"]
    if coverage_value is None:
        missing.append("coverage")
    if runtime_snapshot is None:
        missing.append("runtime_health")
    return {
        "monitor_count": len(monitors),
        "enabled_monitor_count": counts["enabled"],
        "active_monitor_count": counts["active"],
        "learning_monitor_count": counts["learning"],
        "degraded_monitor_count": counts["degraded"],
        "error_monitor_count": counts["error"],
        "suppressed_monitor_count": counts["suppressed"],
        "archived_monitor_count": counts["archived"],
        "open_finding_count": None,
        "critical_finding_count": None,
        "high_finding_count": None,
        "medium_finding_count": None,
        "low_finding_count": None,
        "recovered_finding_count": None,
        "suppressed_finding_count": None,
        "monitor_with_recent_observation_count": None,
        "monitor_without_observation_count": None,
        "stale_monitor_count": None,
        "monitor_with_open_incident_count": None,
        "coverage_state": coverage_value.get("state") if coverage_value else "not_configured",
        "coverage_numerator": numerator,
        "coverage_denominator": denominator,
        "coverage_percentage": (numerator / denominator * 100) if denominator else None,
        "recommendation_count": None,
        "high_risk_gap_count": len(coverage_value.get("high_risk_gaps", [])) if coverage_value else None,
        "runtime_state": (
            ("healthy" if runtime_snapshot.get("live") and runtime_snapshot.get("ready") else "degraded")
            if runtime_snapshot
            else "unavailable"
        ),
        "runtime_backlog": runtime_snapshot.get("backlog") if runtime_snapshot else None,
        "runtime_last_heartbeat": runtime_snapshot.get("last_heartbeat") if runtime_snapshot else None,
        "runtime_worker_count": runtime_snapshot.get("worker_count") if runtime_snapshot else None,
        "last_observation_at": None,
        "last_evaluation_at": None,
        "last_finding_at": None,
        "health": "unknown",
        "reason_codes": ["operational_evidence_incomplete"],
        **evidence(request, "partial", warnings=["Some quality evidence providers are unavailable"], missing=missing),
    }


@router.get("/quality/findings")
def global_findings(
    request: Request,
    state: str | None = None,
    severity: str | None = None,
    monitor_id: str | None = None,
    asset_id: str | None = None,
    incident_id: str | None = None,
    product_id: str | None = None,
    search: str | None = Query(None, max_length=200),
    start: datetime | None = None,
    end: datetime | None = None,
    sort: Literal["newest", "oldest", "severity", "state"] = "newest",
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
):
    repository = repo(request)
    if not hasattr(repository, "list_global_findings"):
        return {
            "items": [],
            "next_cursor": None,
            **evidence(
                request,
                "not_configured",
                warnings=["Global finding read model is unavailable"],
                missing=["global_findings"],
                coverage=[],
            ),
        }
    filters = {
        "state": state,
        "severity": severity,
        "monitor_id": monitor_id,
        "asset_id": asset_id,
        "incident_id": incident_id,
        "product_id": product_id,
        "search": search,
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
    }
    items, next_cursor = repository.list_global_findings(
        *scope(request), filters=filters, sort=sort, limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor, **evidence(request, coverage=["monitor_findings"])}


@router.get("/quality/recommendations")
@router.get("/monitor-recommendations", deprecated=True)
def recommendations(request: Request, limit: int = Query(50, ge=1, le=200)):
    items = repo(request).list_recommendations(*scope(request), limit=limit)
    projected = []
    for item in items:
        value = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        target = value.pop("target", {})
        value["target_display_name"] = next(
            (target.get(k) for k in ("field_id", "asset_id", "table_name") if target.get(k)), "Unknown"
        )
        value.pop("evidence", None)
        projected.append(value)
    return {"items": projected, "next_cursor": None, **evidence(request, coverage=["monitor_recommendations"])}


@router.post("/quality/recommendations/{recommendation_id}/{action}")
@router.post("/monitor-recommendations/{recommendation_id}/{action}", deprecated=True)
def recommendation_transition(
    recommendation_id: str, action: Literal["accept", "reject", "defer"], body: TransitionRequest, request: Request
):
    return repo(request).transition_recommendation(
        *scope(request),
        recommendation_id,
        {"accept": "accepted", "reject": "rejected", "defer": "deferred"}[action],
        actor=body.actor,
    )


@router.get("/quality/coverage")
@router.get("/monitor-coverage", deprecated=True)
def coverage(request: Request):
    value = repo(request).get_coverage(*scope(request))
    if value is None:
        return {
            "scope_type": None,
            "scope_id": None,
            "state": "not_configured",
            "numerator": None,
            "denominator": None,
            "coverage_percentage": None,
            "exclusions": [],
            "by_category": {},
            "high_risk_gaps": [],
            "stale_or_broken_monitors": [],
            "recommendation_count": None,
            **evidence(request, "not_configured", missing=["coverage_policy"], coverage=[]),
        }
    value = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
    denominator = value.get("denominator")
    value["coverage_percentage"] = (value.get("numerator", 0) / denominator * 100) if denominator else None
    return {**value, **evidence(request, coverage=["monitor_coverage"])}


@router.get("/quality/runtime/health")
@router.get("/monitor-runtime/health", deprecated=True)
def runtime_health(request: Request):
    health = getattr(request.app.state, "monitor_runtime_health", None)
    if health is None:
        raise HTTPException(
            503,
            detail={
                "code": "QUALITY_RUNTIME_UNAVAILABLE",
                "message": "monitor runtime unavailable",
                "data_status": "unavailable",
            },
        )
    snapshot = health.snapshot()
    return {
        "state": "healthy" if snapshot.get("live") and snapshot.get("ready") else "degraded",
        "worker_id": snapshot.get("worker_id"),
        "worker_count": snapshot.get("worker_count"),
        "last_heartbeat": snapshot.get("last_heartbeat"),
        "last_successful_cycle": snapshot.get("last_successful_cycle"),
        "last_failed_cycle": snapshot.get("last_failed_cycle"),
        "backlog": snapshot.get("backlog"),
        "active_leases": snapshot.get("active_leases"),
        "expired_leases": snapshot.get("expired_leases"),
        "consecutive_failures": snapshot.get("consecutive_failures"),
        "next_cycle_at": snapshot.get("next_cycle_at"),
        **evidence(request, coverage=["monitor_runtime"]),
    }


@router.get("/quality/runtime/backlog")
@router.get("/monitor-runtime/backlog", deprecated=True)
def backlog(request: Request):
    health = getattr(request.app.state, "monitor_runtime_health", None)
    if health is None:
        raise HTTPException(
            503,
            detail={
                "code": "QUALITY_RUNTIME_UNAVAILABLE",
                "message": "monitor runtime unavailable",
                "data_status": "unavailable",
            },
        )
    return {"state": "available", "backlog": health.backlog, **evidence(request, coverage=["monitor_runtime"])}
