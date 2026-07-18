from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from packages.elastic_store.registry import status as elastic_migration_status
from services.collection_manager import CollectionManagerService
from services.collection_manager.elasticsearch_repository import ElasticsearchCollectionRepository
from services.collection_manager.leases import claim_task, renew_task
from services.collection_manager.memory_repository import InMemoryCollectionRepository
from src.api.store import StoreProtocol, get_store
from src.config.settings import AppSettings, load_settings
from src.core.enterprise_blueprint import enterprise_backlog
from src.core.pillars import PILLAR_REGISTRY, canonical_pillar_value
from src.data_observability.openlineage import OpenLineageValidationError
from src.data_observability.service import DataObservabilityService

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


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


@dataclass(frozen=True)
class StoreBundle:
    store: StoreProtocol


def settings_from_env() -> AppSettings:
    return load_settings()


def make_es_client(settings: AppSettings) -> Elasticsearch:
    return Elasticsearch(
        [settings.elasticsearch.url],
        basic_auth=(settings.elasticsearch.user, settings.elasticsearch.password),
        request_timeout=30,
    )


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
    app.state.settings = resolved_settings
    app.state.store_bundle = resolved_bundle
    if resolved_settings.store_backend.lower() == "elasticsearch":
        repo = ElasticsearchCollectionRepository(make_es_client(resolved_settings))
        repo.readiness()
    else:
        repo = InMemoryCollectionRepository()
    app.state.collection_manager = CollectionManagerService(repo)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.tenant_id = request.headers.get("X-DataObs-Tenant") or resolved_settings.tenant_id
        request.state.principal = {"subject": "local-dev", "scopes": ["dataobs:admin"]}
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    def get_settings(request: Request) -> AppSettings:
        return request.app.state.settings

    def get_stores(request: Request) -> StoreBundle:
        return request.app.state.store_bundle

    async def require_auth(
        settings: AppSettings = Depends(get_settings),
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        authorization: str | None = Header(default=None),
    ) -> None:
        if settings.api_token is None and settings.auth.allow_unauthenticated_dev:
            return
        token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
        if token is None and authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer ") :].strip()
        if token != settings.api_token:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized - valid Bearer token required",
                headers={"WWW-Authenticate": 'Bearer realm="DataObs API"'},
            )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code_map = {400: "bad_request", 401: "unauthorized", 404: "not_found", 405: "method_not_allowed"}
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
        return {"status": "ok", "service": "dataobs-api"}

    @app.get("/readyz", tags=["health"])
    async def readyz(settings: AppSettings = Depends(get_settings)) -> Dict[str, Any]:
        if settings.store_backend != "elasticsearch":
            return {"status": "ok", "store_backend": settings.store_backend, "readiness": "local-memory-mode"}
        try:
            st = elastic_migration_status(make_es_client(settings))
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Elasticsearch readiness check failed: {exc}") from exc
        if not st.get("ready"):
            raise HTTPException(
                status_code=503,
                detail={"message": "Required Elasticsearch migrations are not applied", "migration_status": st},
            )
        return {"status": "ok", "store_backend": settings.store_backend, "migration_status": st}

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
        results = stores.store.list_quality_results(
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

    def dataobs_service(stores: StoreBundle = Depends(get_stores)) -> DataObservabilityService:
        return DataObservabilityService(stores.store)

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
        service: CollectionManagerService = Depends(cm),
        tid: str = Depends(tenant_id),
        limit: int = Query(100, ge=1, le=1000),
        cursor: str | None = None,
    ) -> Dict[str, Any]:
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

    @app.get("/api/v1/monitors", tags=["monitors"], dependencies=[Depends(require_auth)])
    async def list_monitors(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("monitors", tid)}

    @app.get("/api/v1/incidents", tags=["incidents"], dependencies=[Depends(require_auth)])
    async def list_incidents(
        service: CollectionManagerService = Depends(cm), tid: str = Depends(tenant_id)
    ) -> Dict[str, Any]:
        return {"items": service.repo.list("incidents", tid)}

    @app.get(
        "/strategy/enterprise-backlog", response_model=EnterpriseBacklogResponse, dependencies=[Depends(require_auth)]
    )
    async def get_enterprise_backlog() -> Dict[str, Any]:
        return {"backlog": enterprise_backlog(implemented_keys=[])}

    return app
