from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from opentelemetry import metrics, trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from packages.domain_model.incident import IncidentState
from packages.domain_model.investigation import PathwayRouteEdge, PathwayRouteNode, PathwaySearchRequest
from packages.domain_model.workflow import ApprovalState
from packages.elastic_store.registry import status as elastic_migration_status
from services.collection_manager import CollectionManagerService
from services.collection_manager.elasticsearch_repository import ElasticsearchCollectionRepository
from services.collection_manager.leases import claim_task, renew_task
from services.collection_manager.memory_repository import InMemoryCollectionRepository
from services.incident_manager import IncidentManagerService
from services.incident_manager.correlation.coordinator import IncidentCorrelationCoordinator
from services.incident_manager.correlation.elasticsearch_repository import ElasticsearchCorrelationRepository
from services.incident_manager.correlation.repository import InMemoryCorrelationRepository
from services.incident_manager.elasticsearch_repository import ElasticsearchIncidentRepository
from services.incident_manager.flood_control.elasticsearch_repository import ElasticsearchFloodRepository
from services.incident_manager.flood_control.repository import InMemoryFloodRepository
from services.incident_manager.repository import VersionConflict
from services.monitoring.elasticsearch_repository import ElasticsearchMonitorRepository
from services.product_query import ElasticsearchConsoleRepository
from services.product_query.path_search import search_paths
from services.security.role_binding_repository import (
    LastAdministratorError,
    RoleBinding,
    RoleBindingConflict,
    RoleBindingNotFound,
)
from src.api.data_product_routes import create_data_product_router
from src.api.incident_automation_routes import create_incident_automation_router
from src.api.incident_routes import create_incident_workbench_router
from src.api.incident_runtime_routes import create_incident_runtime_router
from src.api.monitor_routes import router as monitor_router
from src.api.pathway_routes import create_pathway_router
from src.api.reliability_routes import create_reliability_router
from src.api.store import StoreProtocol, get_store
from src.api.stream_routes import create_stream_router
from src.config.settings import AppSettings, load_settings
from src.core.enterprise_blueprint import enterprise_backlog
from src.core.pillars import PILLAR_REGISTRY, canonical_pillar_value
from src.data_observability.openlineage import OpenLineageValidationError
from src.data_observability.service import DataObservabilityService, OpenLineageConflictError
from src.platform_operations.health import Criticality, HealthCheck, HealthState, aggregate
from src.platform_operations.slo import evaluate_error_budget
from src.security.audit import security_event
from src.security.authentication import Authenticator
from src.security.authorization import authorize
from src.security.errors import SecurityError
from src.security.permissions import Permission
from src.security.route_policy import permission_for_route, validate_policy
from src.security.tenant_context import resolve_tenant_context
from src.telemetry import telemetry_status

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def _permission_for_request(method: str, path: str) -> Permission:
    permission = permission_for_route(method, path)
    if permission is None:
        raise LookupError("public routes do not have a protected permission")
    return permission


class DataObsModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorInfo
    request_id: str


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    returned: int
    total: int
    has_more: bool


class RulesResponse(BaseModel):
    rules: List[Dict[str, Any]]
    count: int
    pagination: PaginationMeta


class QualityResultsResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int
    pagination: PaginationMeta


class LineageNodesResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    count: int
    pagination: PaginationMeta


class LineageEdgesResponse(BaseModel):
    edges: List[Dict[str, Any]]
    count: int
    pagination: PaginationMeta


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "dataobs-api"
    store_backend: str
    auth_mode: str


class IncidentIngestionMetadata(BaseModel):
    status: Literal["created", "updated", "replayed", "stale"]
    reason: Literal["new_occurrence", "exact_replay", "newer_replay", "stale_replay", "projection_enrichment"]
    occurrence_added: bool
    incident_changed: bool


class FindingIngestionResponse(BaseModel):
    finding: Dict[str, Any]
    incident: Dict[str, Any]
    ingestion: IncidentIngestionMetadata


class RuleRequest(DataObsModel):
    rule_id: Optional[str] = None
    dataset: Optional[str] = None
    check_type: Optional[str] = None
    type: Optional[str] = None
    severity: Optional[str] = "medium"
    enabled: Optional[bool] = True
    config: Optional[Dict[str, Any]] = None


class RuleCreateResponse(BaseModel):
    rule_id: str
    status: str = "created"


class RuleDeleteResponse(BaseModel):
    rule_id: str
    status: str = "deleted"


class QualityResultRequest(DataObsModel):
    id: Optional[str] = None
    check_name: Optional[str] = None
    table: Optional[str] = None
    status: Optional[str] = None
    score: Optional[float] = None
    otel_trace_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class QualityResultCreateResponse(BaseModel):
    id: str
    status: str = "created"


class EnterpriseBacklogResponse(BaseModel):
    backlog: List[Dict[str, Any]]


class LineageImpactResponse(BaseModel):
    root_node: str
    affected: List[str]
    count: int


class DataObservabilityRequest(DataObsModel):
    pass


class RoleBindingRequest(BaseModel):
    issuer: str
    principal_type: Literal["user", "service", "group"]
    principal_id: str
    tenant_id: str
    environments: List[str]
    roles: List[str]
    description: str = ""


class RoleBindingPatch(BaseModel):
    environments: List[str] | None = None
    roles: List[str] | None = None
    active: bool | None = None
    description: str | None = None


@dataclass(frozen=True)
class StoreBundle:
    store: StoreProtocol


def settings_from_env() -> AppSettings:
    return load_settings()


def make_es_client(settings: AppSettings) -> Elasticsearch:
    es = settings.elasticsearch
    kwargs: dict[str, Any] = {
        "verify_certs": es.verify_tls,
        "request_timeout": es.request_timeout,
        "max_retries": max(0, min(es.max_retries, 5)),
        "retry_on_status": (429, 502, 503, 504),
        "retry_on_timeout": False,
    }
    if es.ca_certs:
        kwargs["ca_certs"] = es.ca_certs
    if es.ssl_assert_fingerprint:
        kwargs["ssl_assert_fingerprint"] = es.ssl_assert_fingerprint
    if es.api_key:
        kwargs["api_key"] = es.api_key
    elif es.user or es.password:
        kwargs["basic_auth"] = (es.user, es.password)
    return Elasticsearch([es.url], **kwargs)


def create_store_bundle(settings: AppSettings) -> StoreBundle:
    if settings.store_backend.lower() == "elasticsearch":
        return StoreBundle(store=get_store(es_client=make_es_client(settings), tenant_id=settings.tenant_id))
    return StoreBundle(store=get_store(es_client=None, tenant_id=settings.tenant_id))


def _as_dict(model: DataObsModel) -> Dict[str, Any]:
    return model.model_dump(exclude_none=True) if hasattr(model, "model_dump") else model.dict(exclude_none=True)


def _error_payload(code: str, message: str, request_id: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}, "request_id": request_id}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _paginate(items: List[Dict[str, Any]], limit: int, offset: int) -> Dict[str, Any]:
    total = len(items)
    sliced = items[offset : offset + limit]
    return {
        "items": sliced,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "returned": len(sliced),
            "total": total,
            "has_more": offset + len(sliced) < total,
        },
    }


def create_app(*, settings: AppSettings | None = None, store_bundle: StoreBundle | None = None) -> FastAPI:
    resolved_settings = settings or settings_from_env()
    resolved_bundle = store_bundle or create_store_bundle(resolved_settings)
    app = FastAPI(title="DataObs API", version="1.1.0")
    validate_policy()
    cors = resolved_settings.cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors.allowed_origins),
        allow_methods=list(cors.allowed_methods),
        allow_headers=list(cors.allowed_headers),
        expose_headers=list(cors.exposed_headers),
        allow_credentials=cors.allow_credentials,
        max_age=cors.max_age,
    )
    app.state.settings = resolved_settings
    app.state.authenticator = Authenticator(resolved_settings.auth)
    app.state.store_bundle = resolved_bundle
    meter = metrics.get_meter("dataobs.platform.api")
    request_count = meter.create_counter("dataobs_api_requests_total", unit="{request}")
    request_duration = meter.create_histogram("dataobs_api_request_duration_seconds", unit="s")
    response_size = meter.create_histogram("dataobs_api_response_size_bytes", unit="By")
    in_flight = meter.create_up_down_counter("dataobs_api_in_flight_requests", unit="{request}")
    unhandled = meter.create_counter("dataobs_api_unhandled_exceptions_total", unit="{exception}")
    tracer = trace.get_tracer("dataobs.platform.api")
    if resolved_settings.store_backend.lower() == "elasticsearch":
        repo = ElasticsearchCollectionRepository(make_es_client(resolved_settings))
    else:
        repo = InMemoryCollectionRepository()
    app.state.collection_manager = CollectionManagerService(repo)
    if resolved_settings.store_backend.lower() == "elasticsearch":
        incident_client = make_es_client(resolved_settings)
        incident_repo = ElasticsearchIncidentRepository(incident_client)
        correlation_repo = ElasticsearchCorrelationRepository(incident_client)
        flood_repo = ElasticsearchFloodRepository(incident_client)
    else:
        from services.incident_manager.repository import InMemoryIncidentRepository

        incident_repo = InMemoryIncidentRepository()
        correlation_repo = InMemoryCorrelationRepository()
        flood_repo = InMemoryFloodRepository()
    coordinator = IncidentCorrelationCoordinator(incident_repo, correlation_repo, flood_repo)
    app.state.incident_correlation_coordinator = coordinator
    app.state.incident_manager = IncidentManagerService(incident_repo, coordinator)
    app.state.console_repository = (
        ElasticsearchConsoleRepository(make_es_client(resolved_settings))
        if resolved_settings.store_backend.lower() == "elasticsearch"
        else None
    )
    app.state.monitor_repository = (
        ElasticsearchMonitorRepository(make_es_client(resolved_settings))
        if resolved_settings.store_backend.lower() == "elasticsearch"
        else None
    )
    app.state.security_audit_events = []
    if resolved_settings.store_backend.lower() == "elasticsearch":
        from services.security.elasticsearch_audit_repository import ElasticsearchAuditRepository
        from services.security.elasticsearch_role_binding_repository import ElasticsearchRoleBindingRepository

        security_client = make_es_client(resolved_settings)
        app.state.role_binding_repository = ElasticsearchRoleBindingRepository(
            security_client, request_timeout=resolved_settings.elasticsearch.request_timeout
        )
        app.state.audit_repository = ElasticsearchAuditRepository(
            security_client, request_timeout=resolved_settings.elasticsearch.request_timeout
        )
    else:
        from services.security.memory_role_binding_repository import InMemoryRoleBindingRepository

        app.state.role_binding_repository = InMemoryRoleBindingRepository()
        app.state.audit_repository = None
    if resolved_settings.store_backend.lower() == "elasticsearch":
        from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository

        app.state.data_product_repository = ElasticsearchDataProductRepository(make_es_client(resolved_settings))
    else:
        from services.data_products.memory_repository import MemoryDataProductRepository

    app.state.data_product_repository = MemoryDataProductRepository()

    if resolved_settings.store_backend.lower() == "elasticsearch":
        from services.lineage_intelligence.elasticsearch_repository import ElasticsearchLineageRepository

        app.state.lineage_repository = ElasticsearchLineageRepository(make_es_client(resolved_settings))
    else:
        from services.lineage_intelligence.repository import MemoryLineageRepository

        app.state.lineage_repository = MemoryLineageRepository()

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied
            if len(supplied) <= 128 and supplied.replace("-", "").replace("_", "").replace(".", "").isalnum()
            else str(uuid.uuid4())
        )
        request.state.request_id = request_id
        route = request.scope.get("route")
        template = getattr(route, "path", "unmatched")
        method = request.method.upper()
        started = time.monotonic()
        in_flight_attrs = {"http.route": template, "http.request.method": method}
        in_flight.add(1, in_flight_attrs)
        try:
            with tracer.start_as_current_span(f"{method} {template}", kind=SpanKind.SERVER) as span:
                span.set_attribute("http.route", template)
                span.set_attribute("http.request.method", method)
                span.set_attribute("dataobs.request.id", request_id)
                response = await call_next(request)
                matched_route = request.scope.get("route")
                template = getattr(matched_route, "path", "unmatched")
                span.update_name(f"{method} {template}")
                span.set_attribute("http.route", template)
                span.set_attribute("http.response.status_code", response.status_code)
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR, "server_error"))
        except Exception:
            unhandled.add(1, {"dataobs.error.category": "unhandled", "dataobs.component": "api"})
            raise
        finally:
            in_flight.add(-1, in_flight_attrs)
        family = f"{response.status_code // 100}xx"
        attrs = {
            "http.route": template,
            "http.request.method": method,
            "http.response.status_code_family": family,
            "dataobs.outcome": "success" if response.status_code < 500 else "failure",
        }
        request_count.add(1, attrs)
        request_duration.record(time.monotonic() - started, {k: v for k, v in attrs.items() if k != "dataobs.outcome"})
        if response.headers.get("content-length", "").isdigit():
            response_size.record(
                int(response.headers["content-length"]),
                {"http.route": template, "http.request.method": method, "http.response.status_code_family": family},
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith(("/api/v1/auth", "/api/v1/iam")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        if resolved_settings.runtime.env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def get_settings(request: Request) -> AppSettings:
        return request.app.state.settings

    def get_stores(request: Request) -> StoreBundle:
        return request.app.state.store_bundle

    def get_incident_manager(request: Request) -> IncidentManagerService:
        return request.app.state.incident_manager

    def get_console_repository(request: Request) -> ElasticsearchConsoleRepository:
        repository = request.app.state.console_repository
        if repository is None:
            raise HTTPException(status_code=503, detail="Console projections require the Elasticsearch store backend")
        return repository

    def get_data_product_repository(request: Request):
        return request.app.state.data_product_repository

    def get_lineage_repository(request: Request):
        return request.app.state.lineage_repository

    async def require_auth(
        request: Request,
        settings: AppSettings = Depends(get_settings),
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        authorization: str | None = Header(default=None),
        tenant_selector: str | None = Header(default=None, alias="X-DataObs-Tenant"),
        environment_selector: str | None = Header(default=None, alias="X-DataObs-Environment"),
    ) -> None:
        if authorization and len(authorization) > settings.auth.oidc.maximum_token_bytes + 16:
            raise HTTPException(
                status_code=401, detail={"code": "token_malformed", "message": "Authorization header is too large"}
            )
        token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
        if token is None and authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer ") :].strip()
        try:
            principal = request.app.state.authenticator.authenticate(token)
            principal, context = resolve_tenant_context(
                principal,
                tenant_selector,
                environment_selector or request.query_params.get("environment"),
                _request_id(request),
                request.headers.get("traceparent"),
            )
            route = request.scope.get("route")
            template = getattr(route, "path", request.url.path)
            permission = _permission_for_request(request.method, template)
            authorize(principal, permission)
            request.state.principal = principal
            request.state.tenant_context = context
            request.state.tenant_id = context.tenant_id
            request.state.environment = context.environment
        except LookupError as exc:
            raise HTTPException(
                status_code=403,
                detail={"code": "permission_policy_missing", "message": "Route access is not configured"},
            ) from exc
        except SecurityError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.reason_code, "message": str(exc)},
                headers={"WWW-Authenticate": 'Bearer realm="DataObs API"'} if exc.status_code == 401 else None,
            ) from exc

    app.include_router(monitor_router, dependencies=[Depends(require_auth)])

    @app.get("/api/v1/auth/config", tags=["auth"])
    async def auth_config() -> Dict[str, Any]:
        oidc = resolved_settings.auth.oidc
        return {
            "provider": resolved_settings.auth.provider,
            "issuer": oidc.issuer or None,
            "client_id": oidc.client_id or None,
            "authorization_endpoint": f"{oidc.issuer}/protocol/openid-connect/auth" if oidc.issuer else None,
            "logout_supported": bool(oidc.issuer),
            "scopes": ["openid", *oidc.required_scopes],
        }

    @app.get("/api/v1/auth/me", tags=["auth"], dependencies=[Depends(require_auth)])
    async def auth_me(request: Request) -> Dict[str, Any]:
        principal = request.state.principal
        return {
            "subject": principal.subject,
            "display_name": principal.display_name,
            "principal_type": principal.principal_type,
            "roles": sorted(principal.roles),
            "permissions": sorted(permission.value for permission in principal.permissions),
            "authorised_access": [
                {"tenant_id": item.tenant_id, "environments": sorted(item.environments)}
                for item in sorted(principal.tenant_access)
            ],
            "active_tenant": principal.active_tenant,
            "active_environment": principal.active_environment,
            "authentication_provider": resolved_settings.auth.provider,
            "token_expiry": principal.expires_at.isoformat() if principal.expires_at else None,
        }

    def _binding_document(payload: RoleBindingRequest, request: Request) -> RoleBinding:
        principal = request.state.principal
        if "platform_admin" in payload.roles and "platform_admin" not in principal.roles:
            raise HTTPException(
                status_code=403,
                detail={"code": "role_escalation_denied", "message": "Cannot grant platform administrator"},
            )
        if payload.tenant_id != request.state.tenant_id and "platform_admin" not in principal.roles:
            raise HTTPException(
                status_code=403, detail={"code": "tenant_access_denied", "message": "Cannot manage another tenant"}
            )
        return RoleBinding.new(**payload.model_dump(), actor=principal.subject)

    @app.get("/api/v1/iam/role-bindings", tags=["iam"], dependencies=[Depends(require_auth)])
    async def list_role_bindings(
        request: Request, limit: int = Query(100, ge=1, le=200), cursor: str | None = None
    ) -> Dict[str, Any]:
        items, next_cursor = request.app.state.role_binding_repository.list(
            request.state.tenant_id, limit=limit, after=cursor
        )
        return {"items": [item.document() for item in items], "next_cursor": next_cursor}

    @app.post("/api/v1/iam/role-bindings", status_code=201, tags=["iam"], dependencies=[Depends(require_auth)])
    async def create_role_binding(
        payload: RoleBindingRequest,
        request: Request,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> Dict[str, Any]:
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(
                status_code=400,
                detail={"code": "idempotency_key_required", "message": "A bounded Idempotency-Key is required"},
            )
        document = _binding_document(payload, request)
        try:
            document = request.app.state.role_binding_repository.create(document)
        except RoleBindingConflict as exc:
            raise HTTPException(status_code=409, detail={"code": "idempotency_conflict", "message": str(exc)}) from exc
        request.app.state.security_audit_events.append(
            security_event(
                event_type="iam.binding.created",
                outcome="success",
                reason_code="binding_created",
                principal_id=request.state.principal.subject,
                tenant_id=request.state.tenant_id,
                environment=request.state.environment,
                request_id=_request_id(request),
                route_template="/api/v1/iam/role-bindings",
            )
        )
        return document.document()

    @app.get("/api/v1/iam/role-bindings/{binding_id}", tags=["iam"], dependencies=[Depends(require_auth)])
    async def get_role_binding(binding_id: str, request: Request) -> Dict[str, Any]:
        try:
            document = request.app.state.role_binding_repository.get(binding_id, request.state.tenant_id)
        except RoleBindingNotFound:
            raise HTTPException(status_code=404, detail="Role binding not found")
        return document.document()

    @app.patch("/api/v1/iam/role-bindings/{binding_id}", tags=["iam"], dependencies=[Depends(require_auth)])
    async def patch_role_binding(
        binding_id: str,
        payload: RoleBindingPatch,
        request: Request,
        if_match: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        if not if_match:
            raise HTTPException(
                status_code=428, detail={"code": "if_match_required", "message": "If-Match is required"}
            )
        try:
            document = request.app.state.role_binding_repository.update(
                binding_id,
                request.state.tenant_id,
                if_match=if_match,
                actor=request.state.principal.subject,
                **payload.model_dump(exclude_none=True),
            )
        except RoleBindingNotFound:
            raise HTTPException(
                status_code=404, detail={"code": "role_binding_not_found", "message": "Role binding not found"}
            )
        except RoleBindingConflict as exc:
            raise HTTPException(status_code=409, detail={"code": "etag_mismatch", "message": str(exc)}) from exc
        request.app.state.security_audit_events.append(
            {
                "event_action": "binding_updated",
                "principal_subject": request.state.principal.subject,
                "tenant_id": request.state.tenant_id,
                "binding_id": binding_id,
            }
        )
        return document.document()

    @app.delete(
        "/api/v1/iam/role-bindings/{binding_id}", status_code=204, tags=["iam"], dependencies=[Depends(require_auth)]
    )
    async def delete_role_binding(
        binding_id: str, request: Request, if_match: str | None = Header(default=None)
    ) -> Response:
        if not if_match:
            raise HTTPException(
                status_code=428, detail={"code": "if_match_required", "message": "If-Match is required"}
            )
        try:
            request.app.state.role_binding_repository.disable(
                binding_id, request.state.tenant_id, if_match=if_match, actor=request.state.principal.subject
            )
        except RoleBindingNotFound:
            raise HTTPException(status_code=404, detail="Role binding not found")
        except LastAdministratorError as exc:
            raise HTTPException(status_code=409, detail={"code": "last_administrator", "message": str(exc)}) from exc
        except RoleBindingConflict as exc:
            raise HTTPException(status_code=409, detail={"code": "etag_mismatch", "message": str(exc)}) from exc
        request.app.state.security_audit_events.append(
            security_event(
                event_type="iam.binding.disabled",
                outcome="success",
                reason_code="binding_disabled",
                principal_id=request.state.principal.subject,
                tenant_id=request.state.tenant_id,
                environment=request.state.environment,
                request_id=_request_id(request),
                route_template="/api/v1/iam/role-bindings/{binding_id}",
            )
        )
        return Response(status_code=204)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code_map = {
            400: "bad_request",
            401: "unauthorized",
            404: "not_found",
            405: "method_not_allowed",
            409: "version_conflict",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code_map.get(exc.status_code, "http_error"), str(exc.detail), _request_id(request)),
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = (
            "Not found"
            if exc.status_code == 404
            else ("Method not allowed" if exc.status_code == 405 else str(exc.detail))
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error"),
                message,
                _request_id(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if any(error.get("type") == "json_invalid" for error in errors):
            return JSONResponse(
                status_code=400,
                content=_error_payload("bad_request", "Invalid JSON body", _request_id(request), {"errors": errors}),
            )
        return JSONResponse(
            status_code=422,
            content=_error_payload("validation_error", "Validation error", _request_id(request), {"errors": errors}),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_server_error", "Internal server error", _request_id(request)),
        )

    @app.get("/livez", tags=["health"])
    async def livez() -> Dict[str, Any]:
        return {"status": "ok", "state": "healthy", "component": "api"}

    @app.get("/startupz", tags=["health"])
    async def startupz() -> JSONResponse:
        checks = [
            HealthCheck(
                "configuration",
                HealthState.HEALTHY,
                Criticality.STARTUP,
                "configuration_valid",
                datetime.utcnow().isoformat() + "Z",
                0.0,
            ),
            HealthCheck(
                "route_policy",
                HealthState.HEALTHY,
                Criticality.STARTUP,
                "route_policy_valid",
                datetime.utcnow().isoformat() + "Z",
                0.0,
            ),
            HealthCheck(
                "telemetry",
                HealthState.HEALTHY,
                Criticality.OPTIONAL,
                "initialization_attempted",
                datetime.utcnow().isoformat() + "Z",
                0.0,
            ),
        ]
        return JSONResponse(aggregate("api", checks).as_dict())

    @app.get("/readyz", tags=["health"])
    async def readyz(settings: AppSettings = Depends(get_settings)) -> Dict[str, Any]:
        if settings.store_backend != "elasticsearch":
            return {"status": "ok", "store_backend": settings.store_backend, "readiness": "local-memory-mode"}
        try:
            st = elastic_migration_status(make_es_client(settings))
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"state": "unhealthy", "component": "api", "reason_code": "elasticsearch_unavailable"},
            ) from exc
        if not st.get("ready"):
            raise HTTPException(
                status_code=503,
                detail={"message": "Required Elasticsearch migrations are not applied", "migration_status": st},
            )
        return {"status": "ok", "store_backend": settings.store_backend, "migration_status": st}

    def _platform_view(request: Request, section: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request.app.state.security_audit_events.append(
            security_event(
                event_type="platform.operations.viewed",
                outcome="success",
                reason_code=f"{section}_viewed",
                principal_id=request.state.principal.subject,
                tenant_id=request.state.tenant_id,
                environment=request.state.environment,
                request_id=_request_id(request),
                route_template=f"/api/v1/platform/{section}",
            )
        )
        return payload

    @app.get("/api/v1/platform/{section}", dependencies=[Depends(require_auth)], tags=["platform-operations"])
    async def platform_operations(section: str, request: Request) -> Dict[str, Any]:
        if section not in {
            "health",
            "components",
            "workers",
            "migrations",
            "backups",
            "release",
            "slos",
            "error-budgets",
        }:
            raise HTTPException(status_code=404, detail="Platform operations view not found")
        unknown = {"state": "unknown", "reason_code": "authoritative_evidence_unavailable"}
        if section == "health":
            status = telemetry_status()
            payload = {
                "state": "unknown",
                "component": "platform",
                "telemetry_exporter": {"state": status.exporter_state, "reason_code": status.reason_code},
                "support_matrix": {"state": "unvalidated"},
            }
        elif section == "components":
            payload = {"items": [{"component": "api", "state": "healthy"}, {"component": "elasticsearch", **unknown}]}
        elif section == "error-budgets":
            payload = {
                "items": [
                    evaluate_error_budget(
                        good_events=None,
                        total_events=None,
                        objective=0.995,
                        window_seconds=30 * 86400,
                        data_completeness=0.0,
                    ).as_dict()
                ]
            }
        else:
            payload = {"items": [], **unknown}
        return _platform_view(request, section, payload)

    @app.get("/health", response_model=HealthResponse)
    async def health(settings: AppSettings = Depends(get_settings)) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "dataobs-api",
                "store_backend": settings.store_backend,
                "auth_mode": settings.auth_mode,
            },
            headers={"Deprecation": "true", "Link": "</livez>; rel=successor-version"},
        )

    @app.post(
        "/api/v1/findings",
        status_code=201,
        response_model=FindingIngestionResponse,
        dependencies=[Depends(require_auth)],
    )
    async def create_finding(
        request: Request,
        body: DataObservabilityRequest,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> Dict[str, Any]:
        try:
            return manager.ingest(_as_dict(body), tenant_id=request.state.tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except VersionConflict as exc:
            raise HTTPException(
                status_code=409,
                detail={"message": "Incident changed concurrently", "request_id": request.state.request_id},
            ) from exc

    @app.get("/api/v1/findings", dependencies=[Depends(require_auth)])
    async def list_findings(
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        severity: str | None = None,
        asset_id: str | None = None,
    ) -> Dict[str, Any]:
        items = [f.model_dump(mode="json") for f in manager.repo.list_findings(request.state.tenant_id)]
        items = [
            f
            for f in items
            if (severity is None or f.get("severity") == severity)
            and (asset_id is None or f.get("asset_id") == asset_id)
        ]
        page = _paginate(items, limit, offset)
        return {"findings": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/api/v1/findings/{finding_id}", dependencies=[Depends(require_auth)])
    async def get_finding(
        finding_id: str, request: Request, manager: IncidentManagerService = Depends(get_incident_manager)
    ) -> Dict[str, Any]:
        finding = manager.repo.get_finding(request.state.tenant_id, finding_id)
        if not finding:
            raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
        return finding.model_dump(mode="json")

    @app.get("/api/v1/incidents", dependencies=[Depends(require_auth)])
    async def list_incidents_v1(
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        state: str | None = None,
        severity: str | None = None,
        owner: str | None = None,
        asset_id: str | None = None,
    ) -> Dict[str, Any]:
        items = [i.model_dump(mode="json") for i in manager.repo.list_incidents(request.state.tenant_id)]
        items = [
            i
            for i in items
            if (state is None or i.get("incident_state") == state)
            and (severity is None or i.get("severity") == severity)
            and (owner is None or i.get("owner_team") == owner)
            and (asset_id is None or asset_id in i.get("affected_assets", []))
        ]
        page = _paginate(items, limit, offset)
        return {"incidents": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/api/v1/incidents/{incident_id}", dependencies=[Depends(require_auth)])
    async def get_incident(
        incident_id: str, request: Request, manager: IncidentManagerService = Depends(get_incident_manager)
    ) -> Dict[str, Any]:
        incident = manager.repo.get_incident(request.state.tenant_id, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        return incident.model_dump(mode="json")

    @app.get("/api/v1/incidents/{incident_id}/events", dependencies=[Depends(require_auth)])
    async def incident_events(
        incident_id: str, request: Request, manager: IncidentManagerService = Depends(get_incident_manager)
    ) -> Dict[str, Any]:
        if not manager.repo.get_incident(request.state.tenant_id, incident_id):
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        return {"events": [], "count": 0}

    @app.get("/api/v1/incidents/{incident_id}/evidence", dependencies=[Depends(require_auth)])
    async def incident_evidence(
        incident_id: str, request: Request, manager: IncidentManagerService = Depends(get_incident_manager)
    ) -> Dict[str, Any]:
        incident = manager.repo.get_incident(request.state.tenant_id, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        return {"evidence": incident.most_recent_evidence}

    @app.get("/api/v1/incidents/{incident_id}/impact", dependencies=[Depends(require_auth)])
    async def incident_impact(
        incident_id: str, request: Request, manager: IncidentManagerService = Depends(get_incident_manager)
    ) -> Dict[str, Any]:
        incident = manager.repo.get_incident(request.state.tenant_id, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        return {"affected_assets": incident.affected_assets, "impact_summary": incident.impact_summary}

    async def _incident_transition(
        incident_id: str,
        state: IncidentState,
        request: Request,
        manager: IncidentManagerService,
        body: DataObservabilityRequest | None = None,
    ) -> Dict[str, Any]:
        try:
            return manager.transition(
                request.state.tenant_id, incident_id, state, (_as_dict(body).get("reason") if body else None)
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except VersionConflict as exc:
            raise HTTPException(status_code=409, detail="Incident changed concurrently") from exc

    @app.post("/api/v1/incidents/{incident_id}/acknowledge", dependencies=[Depends(require_auth)])
    async def acknowledge_incident(
        incident_id: str,
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
        body: DataObservabilityRequest | None = None,
    ) -> Dict[str, Any]:
        return await _incident_transition(incident_id, IncidentState.ACKNOWLEDGED, request, manager, body)

    @app.post("/api/v1/incidents/{incident_id}/assign", dependencies=[Depends(require_auth)])
    async def assign_incident(
        incident_id: str,
        request: Request,
        body: DataObservabilityRequest,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> Dict[str, Any]:
        incident = manager.repo.get_incident(request.state.tenant_id, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        data = _as_dict(body)
        incident.owner_team = data.get("owner_team", incident.owner_team)
        try:
            manager.repo.update_incident(incident)
        except VersionConflict as exc:
            raise HTTPException(status_code=409, detail="Incident changed concurrently") from exc
        return incident.model_dump(mode="json")

    @app.post("/api/v1/incidents/{incident_id}/suppress", dependencies=[Depends(require_auth)])
    async def suppress_incident(
        incident_id: str,
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
        body: DataObservabilityRequest | None = None,
    ) -> Dict[str, Any]:
        return await _incident_transition(incident_id, IncidentState.SUPPRESSED, request, manager, body)

    @app.post("/api/v1/incidents/{incident_id}/resolve", dependencies=[Depends(require_auth)])
    async def resolve_incident(
        incident_id: str,
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
        body: DataObservabilityRequest | None = None,
    ) -> Dict[str, Any]:
        return await _incident_transition(incident_id, IncidentState.RESOLVED, request, manager, body)

    @app.post("/api/v1/incidents/{incident_id}/reopen", dependencies=[Depends(require_auth)])
    async def reopen_incident(
        incident_id: str,
        request: Request,
        manager: IncidentManagerService = Depends(get_incident_manager),
        body: DataObservabilityRequest | None = None,
    ) -> Dict[str, Any]:
        return await _incident_transition(incident_id, IncidentState.OPEN, request, manager, body)

    @app.post("/api/v1/incidents/{incident_id}/run-workflow", dependencies=[Depends(require_auth)])
    async def run_incident_workflow(
        incident_id: str,
        request: Request,
        body: DataObservabilityRequest,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> Dict[str, Any]:
        if not manager.repo.get_incident(request.state.tenant_id, incident_id):
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        return {"incident_id": incident_id, "workflow_id": _as_dict(body).get("workflow_id"), "status": "requested"}

    @app.post("/api/v1/incidents/{incident_id}/actions/preview", dependencies=[Depends(require_auth)])
    async def preview_action(
        incident_id: str,
        request: Request,
        body: DataObservabilityRequest,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> Dict[str, Any]:
        data = _as_dict(body)
        try:
            return manager.preview_action(request.state.tenant_id, incident_id, data.get("action_type", ""), data)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/v1/incidents/{incident_id}/actions/execute", dependencies=[Depends(require_auth)])
    async def execute_action(
        incident_id: str,
        request: Request,
        body: DataObservabilityRequest,
        manager: IncidentManagerService = Depends(get_incident_manager),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> Dict[str, Any]:
        data = _as_dict(body)
        try:
            return manager.execute_action(
                request.state.tenant_id,
                incident_id,
                data.get("action_type", ""),
                idempotency_key or data.get("idempotency_key", request.headers.get("X-Request-ID", "none")),
                data,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/v1/incidents/{incident_id}/actions", dependencies=[Depends(require_auth)])
    async def list_actions(
        incident_id: str, request: Request, manager: IncidentManagerService = Depends(get_incident_manager)
    ) -> Dict[str, Any]:
        return {"actions": [a for k, a in manager.repo.actions.items() if f":{incident_id}:" in k]}

    @app.post("/api/v1/approvals/{approval_id}/approve", dependencies=[Depends(require_auth)])
    async def approve(
        approval_id: str,
        request: Request,
        body: DataObservabilityRequest | None = None,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> Dict[str, Any]:
        return manager.decide_approval(
            request.state.tenant_id,
            approval_id,
            ApprovalState.APPROVED,
            _as_dict(body).get("comments") if body else None,
        )

    @app.post("/api/v1/approvals/{approval_id}/reject", dependencies=[Depends(require_auth)])
    async def reject(
        approval_id: str,
        request: Request,
        body: DataObservabilityRequest | None = None,
        manager: IncidentManagerService = Depends(get_incident_manager),
    ) -> Dict[str, Any]:
        return manager.decide_approval(
            request.state.tenant_id,
            approval_id,
            ApprovalState.REJECTED,
            _as_dict(body).get("comments") if body else None,
        )

    @app.get("/rules", response_model=RulesResponse, dependencies=[Depends(require_auth)])
    async def get_rules(
        stores: StoreBundle = Depends(get_stores),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        dataset: str | None = None,
        enabled: bool | None = None,
        severity: str | None = None,
        check_type: str | None = None,
    ) -> Dict[str, Any]:
        rules = stores.store.get_all_rules()
        filtered = [
            rule
            for rule in rules
            if (dataset is None or rule.get("dataset") == dataset)
            and (enabled is None or rule.get("enabled") == enabled)
            and (severity is None or rule.get("severity") == severity)
            and (check_type is None or rule.get("check_type", rule.get("type")) == check_type)
        ]
        page = _paginate(filtered, limit, offset)
        return {"rules": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/quality/results", response_model=QualityResultsResponse, dependencies=[Depends(require_auth)])
    async def get_quality_results(
        request: Request,
        stores: StoreBundle = Depends(get_stores),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        table: str | None = None,
        status: str | None = None,
        dataset: str | None = None,
        check_type: str | None = None,
        severity: str | None = None,
        run_id: str | None = None,
    ) -> Dict[str, Any]:
        store = stores.store
        if resolved_settings.store_backend.lower() == "elasticsearch":
            from src.api.es_store import ElasticsearchStore

            store = ElasticsearchStore(make_es_client(resolved_settings), tenant_id=request.state.tenant_id)
        results = store.list_quality_results(
            limit=1000,
            offset=0,
            table=table,
            status=status,
            dataset=dataset,
            check_type=check_type,
            severity=severity,
            run_id=run_id,
        )
        page = _paginate(results, limit, offset)
        return {"results": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/quality/results/{result_id}", dependencies=[Depends(require_auth)])
    async def get_quality_result(
        result_id: str,
        request: Request,
        stores: StoreBundle = Depends(get_stores),
    ) -> Dict[str, Any]:
        store = stores.store
        if resolved_settings.store_backend.lower() == "elasticsearch":
            from src.api.es_store import ElasticsearchStore

            store = ElasticsearchStore(make_es_client(resolved_settings), tenant_id=request.state.tenant_id)
        result = store.get_quality_result(result_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Quality result '{result_id}' not found")
        return result

    @app.get("/lineage/nodes", response_model=LineageNodesResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_nodes(
        stores: StoreBundle = Depends(get_stores),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        node_type: str | None = None,
        type: str | None = None,
        dataset: str | None = None,
    ) -> Dict[str, Any]:
        nodes = stores.store.get_all_nodes(limit=1000, offset=0, node_type=node_type or type, dataset=dataset)
        page = _paginate(nodes, limit, offset)
        return {"nodes": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/lineage/edges", response_model=LineageEdgesResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_edges(
        stores: StoreBundle = Depends(get_stores),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        source: str | None = None,
        target: str | None = None,
        relation: str | None = None,
        relation_type: str | None = None,
    ) -> Dict[str, Any]:
        edges = stores.store.get_all_edges(
            limit=1000, offset=0, source=source, target=target, relation=relation or relation_type
        )
        page = _paginate(edges, limit, offset)
        return {"edges": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.post("/rules", status_code=201, response_model=RuleCreateResponse, dependencies=[Depends(require_auth)])
    async def create_rule(rule: RuleRequest, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        return {"rule_id": stores.store.add_rule(_as_dict(rule)), "status": "created"}

    @app.delete("/rules/{rule_id}", response_model=RuleDeleteResponse, dependencies=[Depends(require_auth)])
    async def delete_rule(rule_id: str, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        if not stores.store.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
        return {"rule_id": rule_id, "status": "deleted"}

    @app.get(
        "/lineage/impact/{node_id:path}", response_model=LineageImpactResponse, dependencies=[Depends(require_auth)]
    )
    async def get_lineage_impact(node_id: str, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        affected = stores.store.get_downstream_impact(node_id)
        return {"root_node": node_id, "affected": affected, "count": len(affected)}

    @app.post(
        "/quality/results",
        status_code=201,
        response_model=QualityResultCreateResponse,
        dependencies=[Depends(require_auth)],
    )
    async def create_quality_result(
        result: QualityResultRequest, stores: StoreBundle = Depends(get_stores)
    ) -> Dict[str, Any]:
        return {"id": stores.store.save_quality_result(_as_dict(result)), "status": "created"}

    def dataobs_service(request: Request, stores: StoreBundle = Depends(get_stores)) -> DataObservabilityService:
        return DataObservabilityService(
            stores.store,
            getattr(request.state, "tenant_id", "default"),
            getattr(request.state, "environment", "default"),
        )

    # Canonical query surfaces are registered before legacy parameterised aliases.
    from src.api.job_routes import create_job_router
    from src.api.lineage_routes import create_lineage_router
    from src.api.run_routes import create_run_router

    app.include_router(create_job_router(dataobs_service, require_auth))
    app.include_router(create_run_router(dataobs_service, require_auth))
    app.include_router(create_lineage_router(get_lineage_repository, require_auth))

    @app.post("/api/data-observability/assets", status_code=201, dependencies=[Depends(require_auth)])
    async def dataobs_create_asset(
        asset: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.create_or_update_asset(_as_dict(asset))

    @app.get("/api/data-observability/assets", dependencies=[Depends(require_auth)])
    async def dataobs_search_assets(
        service: DataObservabilityService = Depends(dataobs_service),
        q: str | None = None,
        asset_type: str | None = None,
        source_system: str | None = None,
        owner: str | None = None,
        domain: str | None = None,
        health_status: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> Dict[str, Any]:
        assets = service.search_assets(
            q=q,
            asset_type=asset_type,
            source_system=source_system,
            owner=owner,
            domain=domain,
            health_status=health_status,
            limit=limit,
            offset=offset,
        )
        return {"assets": assets, "count": len(assets)}

    @app.get("/api/data-observability/assets/{asset_id:path}/lineage", dependencies=[Depends(require_auth)])
    async def dataobs_get_lineage(
        asset_id: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.get_lineage(asset_id)

    # Kafka DSM projections deliberately expose product state, never message payloads.
    app.state.kafka_dsm = {
        "clusters": [],
        "topics": [],
        "consumer_groups": [],
        "nodes": [],
        "edges": [],
        "pathways": [],
        "slos": {},
    }

    def tenant_items(request: Request, resource: str) -> List[Dict[str, Any]]:
        return [
            item for item in request.app.state.kafka_dsm[resource] if item.get("tenant_id") == request.state.tenant_id
        ]

    @app.get("/api/v1/kafka/clusters", dependencies=[Depends(require_auth)])
    async def kafka_clusters(request: Request, limit: int = Query(100, ge=1, le=1000), cursor: int = Query(0, ge=0)):
        items = sorted(tenant_items(request, "clusters"), key=lambda item: item["id"])
        return {
            "items": items[cursor : cursor + limit],
            "next_cursor": cursor + limit if cursor + limit < len(items) else None,
        }

    @app.get("/api/v1/kafka/clusters/{cluster_id}", dependencies=[Depends(require_auth)])
    async def kafka_cluster(cluster_id: str, request: Request):
        item = next((item for item in tenant_items(request, "clusters") if item["id"] == cluster_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Kafka cluster not found")
        return item

    @app.get("/api/data-observability/assets/{asset_id:path}/health", dependencies=[Depends(require_auth)])
    async def dataobs_get_health(
        asset_id: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return {"asset_id": asset_id, "health_status": service.update_asset_health(asset_id)}

    @app.get("/api/data-observability/assets/{asset_id:path}", dependencies=[Depends(require_auth)])
    async def dataobs_get_asset(
        asset_id: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        asset = service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
        return asset

    @app.post(
        "/api/data-observability/assets/{asset_id:path}/columns", status_code=201, dependencies=[Depends(require_auth)]
    )
    async def dataobs_create_column(
        asset_id: str, column: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.create_or_update_column({**_as_dict(column), "asset_id": asset_id})

    @app.post("/api/data-observability/quality-checks", status_code=201, dependencies=[Depends(require_auth)])
    async def dataobs_create_quality_check(
        check: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        try:
            return service.create_quality_check(_as_dict(check))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/data-observability/quality-runs", status_code=201, dependencies=[Depends(require_auth)])
    async def dataobs_record_quality_run(
        run: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.record_quality_run(_as_dict(run))

    @app.get("/api/data-observability/quality-runs", dependencies=[Depends(require_auth)])
    async def dataobs_search_quality_runs(
        service: DataObservabilityService = Depends(dataobs_service),
        asset_id: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> Dict[str, Any]:
        runs = service.search_quality_runs(
            asset_id=asset_id, status=status, severity=severity, limit=limit, offset=offset
        )
        return {"quality_runs": runs, "count": len(runs)}

    @app.post("/api/data-observability/job-runs", status_code=201, dependencies=[Depends(require_auth)])
    async def dataobs_create_job_run(
        job: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.create_job_run(_as_dict(job))

    @app.get("/api/data-observability/job-runs", dependencies=[Depends(require_auth)])
    async def dataobs_search_job_runs(
        service: DataObservabilityService = Depends(dataobs_service),
        asset_id: str | None = None,
        status: str | None = None,
        source_system: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> Dict[str, Any]:
        runs = service.search_job_runs(
            asset_id=asset_id, status=status, source_system=source_system, limit=limit, offset=offset
        )
        return {"job_runs": runs, "count": len(runs)}

    async def _ingest_openlineage(event: DataObservabilityRequest, service: DataObservabilityService) -> Dict[str, Any]:
        try:
            return service.ingest_openlineage_event(_as_dict(event))
        except OpenLineageValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OpenLineageConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/openlineage/events", status_code=202, dependencies=[Depends(require_auth)])
    async def canonical_openlineage_ingest(
        event: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return await _ingest_openlineage(event, service)

    @app.post("/api/v1/lineage", status_code=201, dependencies=[Depends(require_auth)])
    async def openlineage_ingest(
        event: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return await _ingest_openlineage(event, service)

    @app.post("/api/data-observability/lineage/events", status_code=201, dependencies=[Depends(require_auth)])
    async def dataobs_ingest_lineage_event(
        event: DataObservabilityRequest, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return await _ingest_openlineage(event, service)

    @app.get("/api/v1/runs/{run_id}", dependencies=[Depends(require_auth)])
    async def openlineage_get_run(
        run_id: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        run = service.get_job_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        return run

    @app.get("/api/v1/jobs/{namespace}/{name:path}", dependencies=[Depends(require_auth)])
    async def openlineage_get_job(
        namespace: str, name: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        job = service.get_job(namespace, name)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{namespace}:{name}' not found")
        return job

    @app.get("/api/v1/datasets/{namespace}/{name:path}", dependencies=[Depends(require_auth)])
    async def openlineage_get_dataset(
        namespace: str, name: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        asset_id = f"{namespace}:{name}"
        asset = service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Dataset '{asset_id}' not found")
        return asset

    @app.get("/api/v1/lineage/{asset_id}/upstream", dependencies=[Depends(require_auth)])
    async def openlineage_upstream(
        asset_id: str, depth: int = Query(5, ge=1, le=20), service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.traverse_lineage(asset_id, "upstream", depth)

    @app.get("/api/v1/lineage/{asset_id}/downstream", dependencies=[Depends(require_auth)])
    async def openlineage_downstream(
        asset_id: str, depth: int = Query(5, ge=1, le=20), service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.traverse_lineage(asset_id, "downstream", depth)

    @app.get("/api/v1/lineage/{asset_id}/impact", dependencies=[Depends(require_auth)])
    async def openlineage_impact(
        asset_id: str, depth: int = Query(5, ge=1, le=20), service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.traverse_lineage(asset_id, "downstream", depth)

    @app.get("/api/v1/lineage/{asset_id}/columns/{column}/upstream", dependencies=[Depends(require_auth)])
    async def openlineage_column_upstream(
        asset_id: str, column: str, service: DataObservabilityService = Depends(dataobs_service)
    ) -> Dict[str, Any]:
        return service.get_column_lineage(asset_id, column, "upstream")

    def cm(request: Request) -> CollectionManagerService:
        return request.app.state.collection_manager

    def tenant_id(request: Request) -> str:
        return request.state.tenant_id

    @app.get("/api/v1/pillars", tags=["pillars"], dependencies=[Depends(require_auth)])
    async def api_v1_pillars() -> Dict[str, Any]:
        return {
            "pillars": [
                {
                    "pillar": p.value,
                    "name": d.name,
                    "question": d.question,
                    "capabilities": [c.__dict__ for c in d.capabilities],
                }
                for p, d in PILLAR_REGISTRY.items()
            ]
        }

    @app.get("/api/v1/migrations", tags=["migrations"], dependencies=[Depends(require_auth)])
    async def api_v1_migrations(settings: AppSettings = Depends(get_settings)) -> Dict[str, Any]:
        if settings.store_backend != "elasticsearch":
            return {"status": "local-memory-mode", "required": ["0001_product_foundation"]}
        return elastic_migration_status(make_es_client(settings))

    @app.post("/api/v1/tenants", status_code=201, tags=["tenants"], dependencies=[Depends(require_auth)])
    async def create_tenant(
        payload: DataObservabilityRequest, request: Request, service: CollectionManagerService = Depends(cm)
    ) -> Dict[str, Any]:
        return service.create_tenant(_as_dict(payload), _request_id(request))

    @app.get("/api/v1/tenants", tags=["tenants"], dependencies=[Depends(require_auth)])
    async def list_tenants(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("tenants", tid)}

    @app.post("/api/v1/sources", status_code=201, tags=["sources"], dependencies=[Depends(require_auth)])
    async def create_source(
        payload: DataObservabilityRequest,
        request: Request,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.create_source(tid, _as_dict(payload), _request_id(request))

    @app.get("/api/v1/sources", tags=["sources"], dependencies=[Depends(require_auth)])
    async def list_sources(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("sources", tid)}

    @app.post("/api/v1/integrations", status_code=201, tags=["integrations"], dependencies=[Depends(require_auth)])
    async def create_integration(
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.register("integrations", tid, _as_dict(payload), "integration")

    @app.get("/api/v1/integrations", tags=["integrations"], dependencies=[Depends(require_auth)])
    async def list_integrations(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("integrations", tid)}

    @app.post("/api/v1/collectors", status_code=201, tags=["collectors"], dependencies=[Depends(require_auth)])
    async def create_collector(
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.register("collectors", tid, _as_dict(payload), "collector")

    @app.get("/api/v1/collectors", tags=["collectors"], dependencies=[Depends(require_auth)])
    async def list_collectors(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("collectors", tid)}

    @app.post("/api/v1/collectors/{collector_id}/heartbeat", tags=["collectors"], dependencies=[Depends(require_auth)])
    async def collector_heartbeat(
        collector_id: str,
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.heartbeat("collectors", tid, collector_id, _as_dict(payload))

    @app.post("/api/v1/scanners", status_code=201, tags=["scanners"], dependencies=[Depends(require_auth)])
    async def create_scanner(
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.register("scanners", tid, _as_dict(payload), "scanner")

    @app.get("/api/v1/scanners", tags=["scanners"], dependencies=[Depends(require_auth)])
    async def list_scanners(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("scanners", tid)}

    @app.post("/api/v1/scanners/{scanner_id}/heartbeat", tags=["scanners"], dependencies=[Depends(require_auth)])
    async def scanner_heartbeat(
        scanner_id: str,
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.heartbeat("scanners", tid, scanner_id, _as_dict(payload))

    @app.get("/api/v1/scanners/{scanner_id}/tasks", tags=["scanner tasks"], dependencies=[Depends(require_auth)])
    async def scanner_tasks(
        scanner_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.tasks_for_scanner(tid, scanner_id)}

    @app.post(
        "/api/v1/scanners/{scanner_id}/tasks/{task_id}/claim",
        tags=["scanner tasks"],
        dependencies=[Depends(require_auth)],
    )
    async def scanner_task_claim(
        scanner_id: str, task_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return claim_task(service.repo, tid, scanner_id, task_id)

    @app.post(
        "/api/v1/scanners/{scanner_id}/tasks/{task_id}/renew",
        tags=["scanner tasks"],
        dependencies=[Depends(require_auth)],
    )
    async def scanner_task_renew(
        scanner_id: str, task_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return renew_task(service.repo, tid, scanner_id, task_id)

    @app.post(
        "/api/v1/scanners/{scanner_id}/tasks/{task_id}/fail",
        tags=["scanner tasks"],
        dependencies=[Depends(require_auth)],
    )
    async def scanner_task_fail(
        scanner_id: str,
        task_id: str,
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        task = service.repo.get("tasks", task_id, tid)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
        return service.repo.upsert("tasks", {**task, "status": "failed", "error": _as_dict(payload)})

    @app.post(
        "/api/v1/scanners/{scanner_id}/tasks/{task_id}/ack",
        tags=["scanner tasks"],
        dependencies=[Depends(require_auth)],
    )
    async def scanner_task_ack(
        scanner_id: str, task_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return service.ack_task(tid, scanner_id, task_id)

    @app.post(
        "/api/v1/scanners/{scanner_id}/tasks/{task_id}/results",
        tags=["scanner tasks"],
        dependencies=[Depends(require_auth)],
    )
    async def scanner_task_result(
        scanner_id: str,
        task_id: str,
        payload: DataObservabilityRequest,
        request: Request,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> Dict[str, Any]:
        return service.submit_result(tid, scanner_id, task_id, _as_dict(payload), idempotency_key)

    @app.post("/api/v1/scan-policies", status_code=201, tags=["scan policies"], dependencies=[Depends(require_auth)])
    async def create_scan_policy(
        payload: DataObservabilityRequest,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
    ) -> Dict[str, Any]:
        return service.create_policy(tid, _as_dict(payload))

    @app.get("/api/v1/scan-policies", tags=["scan policies"], dependencies=[Depends(require_auth)])
    async def list_scan_policies(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("policies", tid)}

    @app.get("/api/v1/assets", tags=["assets"], dependencies=[Depends(require_auth)])
    async def list_assets(
        request: Request,
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
        environment: str | None = Query(None, min_length=1),
        search: str | None = Query(None, max_length=256),
        limit: int = Query(100, ge=1, le=100),
        cursor: str | None = None,
        asset_type: str | None = Query(None, max_length=64),
        owner_team: str | None = Query(None, max_length=128),
        source: str | None = Query(None, max_length=128),
    ) -> Dict[str, Any]:
        repository = request.app.state.console_repository
        if repository is not None and environment is not None:
            from services.product_query.pagination import decode_cursor, encode_cursor

            try:
                search_after = decode_cursor(cursor)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            found = repository.assets(
                tid,
                environment,
                size=limit + 1,
                search=search,
                search_after=search_after,
                asset_type=asset_type,
                owner_team=owner_team,
                source=source,
            )
            next_cursor = encode_cursor(found[limit - 1].get("_sort", [])) if len(found) > limit else None
            items = [{key: value for key, value in item.items() if key != "_sort"} for item in found[:limit]]
            return {
                "items": items,
                "next_cursor": next_cursor,
                "data_status": "complete" if found else "unknown",
                "observed_at": datetime.now().astimezone().isoformat(),
                "source_coverage": ["elasticsearch"],
                "confidence": 1.0 if found else None,
                "warnings": [] if found else ["No matching assets were observed"],
                "evidence": [],
            }
        items = service.repo.list("assets", tid)[:limit]
        return {"items": items, "next_cursor": None}

    @app.get("/api/v1/assets/{asset_id}/schema", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_schema(
        asset_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return service.repo.get("schema_current", asset_id, tid) or {"asset_id": asset_id}

    @app.get("/api/v1/assets/{asset_id}/schema/changes", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_schema_changes(asset_id: str) -> Dict[str, Any]:
        return {"items": []}

    @app.get("/api/v1/assets/{asset_id}/freshness", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_freshness(
        asset_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return service.repo.get("freshness_current", asset_id, tid) or {"asset_id": asset_id}

    @app.get("/api/v1/assets/{asset_id}/profile", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_profile(
        asset_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return service.repo.get("profile_current", asset_id, tid) or {"asset_id": asset_id}

    @app.get("/api/v1/assets/{asset_id}/quality", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_quality(
        asset_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return service.repo.get("quality_current", asset_id, tid) or {"asset_id": asset_id}

    @app.get("/api/v1/assets/{asset_id}/lineage", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_lineage(asset_id: str) -> Dict[str, Any]:
        return {"asset_id": asset_id, "upstream": [], "downstream": []}

    @app.get("/api/v1/assets/{asset_id}/impact", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset_impact(asset_id: str) -> Dict[str, Any]:
        return {"asset_id": asset_id, "affected": []}

    @app.get("/api/v1/assets/{asset_id}", tags=["assets"], dependencies=[Depends(require_auth)])
    async def get_asset(
        asset_id: str, service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        asset = service.repo.get("assets", asset_id)
        if not asset or asset.get("tenant_id") != tid:
            raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
        return asset

    @app.get("/api/v1/incidents", tags=["incidents"], dependencies=[Depends(require_auth)])
    async def list_incidents(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("incidents", tid)}

    @app.get("/api/v1/command-center", tags=["console"], dependencies=[Depends(require_auth)])
    async def command_center(
        request: Request,
        environment: str = Query(..., min_length=1),
        start: datetime | None = Query(None),
        end: datetime | None = Query(None),
        repository: ElasticsearchConsoleRepository = Depends(get_console_repository),
    ) -> Dict[str, Any]:
        return repository.command_center(request.state.tenant_id, environment, start, end)

    @app.get("/api/v1/topology", tags=["console"], dependencies=[Depends(require_auth)])
    async def console_topology(
        request: Request,
        environment: str = Query(..., min_length=1),
        source_integration: str | None = None,
        max_nodes: int = Query(500, ge=1, le=1000),
        max_edges: int = Query(1250, ge=1, le=2500),
        repository: ElasticsearchConsoleRepository = Depends(get_console_repository),
    ) -> Dict[str, Any]:
        return repository.topology(
            request.state.tenant_id, environment, max_nodes=max_nodes, max_edges=max_edges, source=source_integration
        )

    @app.get("/api/v1/assets/{asset_id}/{section}", tags=["assets"], dependencies=[Depends(require_auth)])
    async def asset_section(
        asset_id: str,
        section: str,
        request: Request,
        environment: str = Query(..., min_length=1),
        repository: ElasticsearchConsoleRepository = Depends(get_console_repository),
    ) -> Dict[str, Any]:
        allowed_sections = {
            "summary",
            "schema",
            "quality",
            "freshness",
            "lineage",
            "usage",
            "incidents",
            "changes",
            "slos",
            "cost",
            "related",
            "impact",
            "annotations",
        }
        if section not in allowed_sections:
            raise HTTPException(status_code=404, detail="Unknown asset section")
        if section == "cost":
            return {
                "asset_id": asset_id,
                "data_status": "not_configured",
                "observed_at": None,
                "source_coverage": [],
                "confidence": None,
                "warnings": ["Cost collection is not configured"],
                "evidence": [],
                "request_id": getattr(request.state, "request_id", None),
                "trace_id": None,
            }
        document = repository.asset_section(request.state.tenant_id, environment, asset_id, section)
        if document is None:
            return {
                "asset_id": asset_id,
                "data_status": "not_configured",
                "observed_at": None,
                "source_coverage": [],
                "confidence": None,
                "warnings": [f"{section.capitalize()} collection is not configured or has no observations"],
                "evidence": [],
                "request_id": getattr(request.state, "request_id", None),
                "trace_id": None,
            }
        return document

    @app.post("/api/v1/pathway-explorer/search", tags=["pathways"], dependencies=[Depends(require_auth)])
    async def pathway_search(
        body: PathwaySearchRequest,
        request: Request,
        environment: str = Query(..., min_length=1),
        repository: ElasticsearchConsoleRepository = Depends(get_console_repository),
    ) -> Dict[str, Any]:
        topology = repository.topology(request.state.tenant_id, environment, max_nodes=1000, max_edges=2500)
        nodes = [
            PathwayRouteNode(
                id=str(item.get("id", item.get("node_id", item.get("_id")))),
                name=str(item.get("name", item.get("id", "unknown"))),
                node_type=str(item.get("node_type", item.get("type", "unknown"))),
            )
            for item in topology["nodes"]
        ]
        edges = [PathwayRouteEdge.model_validate(item) for item in topology["edges"]]
        complete, partial, excluded, truncated = search_paths(
            nodes,
            edges,
            body.start_node_id,
            body.end_node_id,
            max_hops=body.max_hops,
            max_paths=body.max_paths,
            minimum_confidence=body.minimum_confidence,
            direction=body.direction,
            include_partial=body.include_partial,
        )
        return {
            "best_path": complete[0] if complete else None,
            "alternative_paths": complete[1:],
            "partial_paths": partial,
            "excluded_path_count": excluded,
            "truncated": truncated or topology["truncated"],
            "data_status": "complete" if complete else "partial" if partial else "unknown",
            "observed_at": datetime.now().astimezone().isoformat(),
            "source_coverage": ["elasticsearch"],
            "confidence": complete[0].confidence if complete else None,
            "warnings": ["Traversal was bounded"] if truncated else [],
            "evidence": [],
        }

    @app.get("/api/v1/topology/nodes/{node_id}", tags=["console"], dependencies=[Depends(require_auth)])
    @app.get("/api/v1/entities/{node_id}/summary", tags=["console"], dependencies=[Depends(require_auth)])
    async def console_entity(
        node_id: str,
        request: Request,
        environment: str = Query(..., min_length=1),
        repository: ElasticsearchConsoleRepository = Depends(get_console_repository),
    ) -> Dict[str, Any]:
        entity = repository.entity(request.state.tenant_id, environment, node_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    @app.get("/api/v1/events/stream", tags=["console"], dependencies=[Depends(require_auth)])
    async def console_events(request: Request, environment: str = Query(..., min_length=1)) -> StreamingResponse:
        async def stream():
            event_id = request.headers.get("Last-Event-ID", "0")
            yield f'retry: 5000\nid: {event_id}\nevent: keepalive\ndata: {{"schema_version":"1","tenant":"{request.state.tenant_id}","environment":"{environment}"}}\n\n'

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    @app.get(
        "/strategy/enterprise-backlog", response_model=EnterpriseBacklogResponse, dependencies=[Depends(require_auth)]
    )
    async def get_enterprise_backlog() -> Dict[str, Any]:
        return {"backlog": enterprise_backlog(implemented_keys=[])}

    app.include_router(create_stream_router(get_console_repository, require_auth))
    app.include_router(create_reliability_router(get_console_repository, require_auth))
    app.include_router(create_pathway_router(get_console_repository, require_auth))
    app.include_router(create_data_product_router(get_data_product_repository, require_auth))
    app.include_router(create_incident_workbench_router(require_auth))
    app.include_router(create_incident_automation_router(require_auth))
    app.include_router(create_incident_runtime_router(require_auth))

    return app
