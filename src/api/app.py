"""FastAPI application factory for the DataObs API.

The public route shapes intentionally mirror the original
``BaseHTTPRequestHandler`` implementation while moving request handling to
FastAPI, Pydantic models, and explicit dependency injection.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
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
    """Base model that allows legacy clients to send additional fields."""

    model_config = ConfigDict(extra="allow")


APISettings = AppSettings


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "dataobs-api"
    store_backend: str
    auth_mode: str


class ErrorResponse(BaseModel):
    error: str
    details: Optional[Any] = None


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


class RulesResponse(BaseModel):
    rules: List[Dict[str, Any]]
    count: int


class LineageNodesResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    count: int


class LineageEdgesResponse(BaseModel):
    edges: List[Dict[str, Any]]
    count: int


class LineageImpactResponse(BaseModel):
    root_node: str
    affected: List[str]
    count: int


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


class QualityResultsResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int


class EnterpriseBacklogResponse(BaseModel):
    backlog: List[Dict[str, Any]]


@dataclass(frozen=True)
class StoreBundle:
    """Injected store handles used by route dependencies."""

    store: StoreProtocol


def settings_from_env() -> APISettings:
    """Load API settings from the unified typed settings layer."""
    return load_settings()


def make_es_client(settings: APISettings) -> Elasticsearch:
    return Elasticsearch(
        [settings.elasticsearch.url],
        basic_auth=(settings.elasticsearch.user, settings.elasticsearch.password),
        request_timeout=30,
    )


def create_store_bundle(settings: APISettings) -> StoreBundle:
    """Create the production store bundle from settings."""
    es_client: Elasticsearch | None = None
    if settings.store_backend.lower() == "elasticsearch":
        es_client = make_es_client(settings)
        store = get_store(es_client=es_client, tenant_id=settings.tenant_id)
        return StoreBundle(store=store)

    store = get_store(es_client=None, tenant_id=settings.tenant_id)
    return StoreBundle(store=store)


def _as_dict(model: DataObsModel) -> Dict[str, Any]:
    """Return a request model as a dict excluding omitted/None fields."""
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)  # Pydantic v2
    return model.dict(exclude_none=True)  # Pydantic v1


def create_app(
    *,
    settings: APISettings | None = None,
    store_bundle: StoreBundle | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved_settings = settings or settings_from_env()
    resolved_bundle = store_bundle or create_store_bundle(resolved_settings)

    if resolved_settings.api_token is None:
        if not resolved_settings.auth.allow_unauthenticated_dev:
            logger.warning("API_TOKEN is not set and unauthenticated dev mode is disabled.")
        else:
            logger.warning(
                "API_TOKEN is not set — running in explicit unauthenticated dev mode. "
                "Set API_TOKEN in production."
            )
    else:
        logger.info("Bearer token authentication enabled.")

    app = FastAPI(
        title="DataObs API",
        version="1.0.0",
        description="REST API for DataObs rules, lineage, quality results, and strategy backlog.",
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            405: {"model": ErrorResponse},
        },
    )

    app.state.settings = resolved_settings
    app.state.store_bundle = resolved_bundle

    def get_settings(request: Request) -> APISettings:
        return request.app.state.settings

    def get_stores(request: Request) -> StoreBundle:
        return request.app.state.store_bundle

    async def require_auth(
        settings: APISettings = Depends(get_settings),
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        authorization: str | None = Header(default=None),
    ) -> None:
        if settings.api_token is None:
            if settings.auth.allow_unauthenticated_dev:
                return
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized - valid Bearer token required",
                headers={"WWW-Authenticate": 'Bearer realm="DataObs API"'},
            )

        token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
        # Preserve the legacy parser's exact "Bearer " prefix behavior for unusual clients.
        if token is None and authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer "):].strip()
        if token != settings.api_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized - valid Bearer token required",
                headers={"WWW-Authenticate": 'Bearer realm="DataObs API"'},
            )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail)},
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = "Not found" if exc.status_code == 404 else str(exc.detail)
        if exc.status_code == 405:
            message = "Method not allowed"
        return JSONResponse(status_code=exc.status_code, content={"error": message})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if any(error.get("type") == "json_invalid" for error in errors):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid JSON body", "details": errors},
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Validation error", "details": errors},
        )

    @app.get("/health", response_model=HealthResponse)
    async def health(settings: APISettings = Depends(get_settings)) -> Dict[str, Any]:
        return {
            "status": "ok",
            "service": "dataobs-api",
            "store_backend": settings.store_backend,
            "auth_mode": settings.auth_mode,
        }

    @app.get("/rules", response_model=RulesResponse, dependencies=[Depends(require_auth)])
    async def get_rules(stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        rules = stores.store.get_all_rules()
        return {"rules": rules, "count": len(rules)}

    @app.post("/rules", status_code=201, response_model=RuleCreateResponse, dependencies=[Depends(require_auth)])
    async def create_rule(rule: RuleRequest, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        rule_id = stores.store.add_rule(_as_dict(rule))
        return {"rule_id": rule_id, "status": "created"}

    @app.delete("/rules/{rule_id}", response_model=RuleDeleteResponse, dependencies=[Depends(require_auth)])
    async def delete_rule(rule_id: str, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        if not rule_id:
            raise HTTPException(status_code=400, detail="rule_id is required")
        deleted = stores.store.delete_rule(rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
        return {"rule_id": rule_id, "status": "deleted"}

    @app.get("/lineage/nodes", response_model=LineageNodesResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_nodes(stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        nodes = stores.store.get_all_nodes()
        return {"nodes": nodes, "count": len(nodes)}

    @app.get("/lineage/edges", response_model=LineageEdgesResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_edges(stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        edges = stores.store.get_all_edges()
        return {"edges": edges, "count": len(edges)}

    @app.get("/lineage/impact/{node_id:path}", response_model=LineageImpactResponse, dependencies=[Depends(require_auth)])
    async def get_lineage_impact(node_id: str, stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        if not node_id:
            raise HTTPException(status_code=400, detail="node_id is required")
        affected = stores.store.get_downstream_impact(node_id)
        return {"root_node": node_id, "affected": affected, "count": len(affected)}

    @app.get("/quality/results", response_model=QualityResultsResponse, dependencies=[Depends(require_auth)])
    async def get_quality_results(stores: StoreBundle = Depends(get_stores)) -> Dict[str, Any]:
        results = stores.store.list_quality_results()
        return {"results": results, "count": len(results)}

    @app.post(
        "/quality/results",
        status_code=201,
        response_model=QualityResultCreateResponse,
        dependencies=[Depends(require_auth)],
    )
    async def create_quality_result(
        result: QualityResultRequest,
        stores: StoreBundle = Depends(get_stores),
    ) -> Dict[str, Any]:
        doc_id = stores.store.save_quality_result(_as_dict(result))
        return {"id": doc_id, "status": "created"}

    @app.get("/strategy/enterprise-backlog", response_model=EnterpriseBacklogResponse, dependencies=[Depends(require_auth)])
    async def get_enterprise_backlog() -> Dict[str, Any]:
        backlog = enterprise_backlog(implemented_keys=[])
        return {"backlog": backlog}

    return app
