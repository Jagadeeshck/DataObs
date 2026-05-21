from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.store import StoreProtocol, get_store
from src.config.settings import AppSettings, load_settings
from src.core.enterprise_blueprint import enterprise_backlog

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


@dataclass(frozen=True)
class StoreBundle:
    store: StoreProtocol


def settings_from_env() -> AppSettings:
    return load_settings()


def make_es_client(settings: AppSettings) -> Elasticsearch:
    return Elasticsearch([settings.elasticsearch.url], basic_auth=(settings.elasticsearch.user, settings.elasticsearch.password), request_timeout=30)


def create_store_bundle(settings: AppSettings) -> StoreBundle:
    if settings.store_backend.lower() == "elasticsearch":
        return StoreBundle(store=get_store(es_client=make_es_client(settings), tenant_id=settings.tenant_id))
    return StoreBundle(store=get_store(es_client=None, tenant_id=settings.tenant_id))


def _as_dict(model: DataObsModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _error_payload(code: str, message: str, request_id: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}, "request_id": request_id}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _paginate(items: List[Dict[str, Any]], limit: int, offset: int) -> Dict[str, Any]:
    total = len(items)
    sliced = items[offset:offset + limit]
    return {"items": sliced, "pagination": {"limit": limit, "offset": offset, "returned": len(sliced), "total": total, "has_more": offset + len(sliced) < total}}


def create_app(*, settings: AppSettings | None = None, store_bundle: StoreBundle | None = None) -> FastAPI:
    resolved_settings = settings or settings_from_env()
    resolved_bundle = store_bundle or create_store_bundle(resolved_settings)
    app = FastAPI(title="DataObs API", version="1.0.0")
    app.state.settings = resolved_settings
    app.state.store_bundle = resolved_bundle

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    def get_settings(request: Request) -> AppSettings:
        return request.app.state.settings

    def get_stores(request: Request) -> StoreBundle:
        return request.app.state.store_bundle

    async def require_auth(settings: AppSettings = Depends(get_settings), credentials: HTTPAuthorizationCredentials | None = Depends(_bearer), authorization: str | None = Header(default=None)) -> None:
        if settings.api_token is None and settings.auth.allow_unauthenticated_dev:
            return
        token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
        if token is None and authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer "):].strip()
        if token != settings.api_token:
            raise HTTPException(status_code=401, detail="Unauthorized - valid Bearer token required", headers={"WWW-Authenticate": 'Bearer realm="DataObs API"'})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code_map = {400: "bad_request", 401: "unauthorized", 404: "not_found", 405: "method_not_allowed"}
        return JSONResponse(status_code=exc.status_code, content=_error_payload(code_map.get(exc.status_code, "http_error"), str(exc.detail), _request_id(request)), headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        msg = "Not found" if exc.status_code == 404 else ("Method not allowed" if exc.status_code == 405 else str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=_error_payload({404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error"), msg, _request_id(request)))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errors):
            return JSONResponse(status_code=400, content=_error_payload("bad_request", "Invalid JSON body", _request_id(request), {"errors": errors}))
        return JSONResponse(status_code=422, content=_error_payload("validation_error", "Validation error", _request_id(request), {"errors": errors}))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception request_id=%s", _request_id(request))
        return JSONResponse(status_code=500, content=_error_payload("internal_server_error", "Internal server error", _request_id(request)))

    @app.get("/health", response_model=HealthResponse)
    async def health(settings: AppSettings = Depends(get_settings)) -> Dict[str, Any]:
        return {"status": "ok", "service": "dataobs-api", "store_backend": settings.store_backend, "auth_mode": settings.auth_mode}

    @app.get("/rules", response_model=RulesResponse, dependencies=[Depends(require_auth)])
    async def get_rules(stores: StoreBundle = Depends(get_stores), limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0), dataset: str | None = None, enabled: bool | None = None, severity: str | None = None, check_type: str | None = None) -> Dict[str, Any]:
        rules = stores.store.get_all_rules()
        filtered = [r for r in rules if (dataset is None or r.get("dataset") == dataset) and (enabled is None or r.get("enabled") == enabled) and (severity is None or r.get("severity") == severity) and (check_type is None or r.get("check_type", r.get("type")) == check_type)]
        page = _paginate(filtered, limit, offset)
        return {"rules": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/quality/results", response_model=QualityResultsResponse, dependencies=[Depends(require_auth)])
    async def get_quality_results(stores: StoreBundle = Depends(get_stores), limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0), table: str | None = None, status: str | None = None, dataset: str | None = None, check_type: str | None = None, severity: str | None = None, run_id: str | None = None) -> Dict[str, Any]:
        results = stores.store.list_quality_results(limit=1000, offset=0, table=table, status=status, dataset=dataset, check_type=check_type, severity=severity, run_id=run_id)
        page = _paginate(results, limit, offset)
        return {"results": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/lineage/nodes", response_model=LineageNodesResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_nodes(stores: StoreBundle = Depends(get_stores), limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0), node_type: str | None = None, type: str | None = None, dataset: str | None = None) -> Dict[str, Any]:
        nodes = stores.store.get_all_nodes(limit=1000, offset=0, node_type=node_type or type, dataset=dataset)
        page = _paginate(nodes, limit, offset)
        return {"nodes": page["items"], "count": len(page["items"]), "pagination": page["pagination"]}

    @app.get("/lineage/edges", response_model=LineageEdgesResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_edges(stores: StoreBundle = Depends(get_stores), limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0), source: str | None = None, target: str | None = None, relation: str | None = None, relation_type: str | None = None) -> Dict[str, Any]:
        edges = stores.store.get_all_edges(limit=1000, offset=0, source=source, target=target, relation=relation or relation_type)
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

    @app.get("/lineage/impact/{node_id:path}", response_model=LineageImpactResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_impact(node_id: str, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        affected = stores.store.get_downstream_impact(node_id)
        return {"root_node": node_id, "affected": affected, "count": len(affected)}

    @app.post("/quality/results", status_code=201, response_model=QualityResultCreateResponse, dependencies=[Depends(require_auth)])
    async def create_quality_result(result: QualityResultRequest, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        return {"id": stores.store.save_quality_result(_as_dict(result)), "status": "created"}

    @app.get("/strategy/enterprise-backlog", response_model=EnterpriseBacklogResponse, dependencies=[Depends(require_auth)])
    async def get_enterprise_backlog() -> Dict[str, Any]:
        return {"backlog": enterprise_backlog(implemented_keys=[])}

    return app
