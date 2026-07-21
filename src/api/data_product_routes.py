"""Typed HTTP boundary for scoped Data Product workflows."""

from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from packages.domain_model.data_product import DataProduct, DataProductCriticality, DataProductOutput, DataProductOwner
from services.data_products.repository import ProductVersionConflict
from services.data_products.service import DataProductService


class ProductWrite(BaseModel):
    id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    domain: str = Field(min_length=1, max_length=128)
    criticality: DataProductCriticality
    owner: DataProductOwner
    outputs: list[DataProductOutput] = Field(default_factory=list, max_length=200)
    lifecycle_state: Literal["draft", "active", "deprecated", "archived"] = "draft"


class ActionRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)


class ProductEnvelope(BaseModel):
    product: DataProduct
    data_status: Literal["available"] = "available"
    source_coverage: float = 1
    confidence: float = 1
    warnings: list[str] = Field(default_factory=list)
    request_id: str
    trace_id: str


def create_data_product_router(
    repository_provider: Callable[..., Any], auth_dependency: Callable[..., Any]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/data-products", tags=["data-products"], dependencies=[Depends(auth_dependency)])

    def service(repository: Any = Depends(repository_provider)) -> DataProductService:
        return DataProductService(repository)

    def envelope(product: DataProduct, request: Request, response: Response) -> dict[str, Any]:
        response.headers["ETag"] = product.etag
        request_id = request.state.request_id
        return ProductEnvelope(
            product=product, request_id=request_id, trace_id=request.headers.get("traceparent", request_id)
        ).model_dump(mode="json")

    @router.get("")
    def list_products(
        request: Request,
        environment: str = Query(..., min_length=1, max_length=64),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None, max_length=2048),
        domain: str | None = Query(None, max_length=128),
        lifecycle: str | None = Query(None, max_length=32),
        owner: str | None = Query(None, max_length=128),
        search: str | None = Query(None, max_length=200),
        include_archived: bool = False,
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        filters = {
            "domain": domain,
            "lifecycle": lifecycle,
            "owner": owner,
            "search": search,
            "include_archived": include_archived,
        }
        products = list(
            application.repository.list_products(
                request.state.tenant_id, environment, limit=limit, cursor=cursor, filters=filters
            )
        )
        return {
            "items": products,
            "data_status": "available",
            "source_coverage": 1,
            "confidence": 1,
            "warnings": [],
            "request_id": request.state.request_id,
            "trace_id": request.headers.get("traceparent", request.state.request_id),
            "pagination": {"limit": limit, "next_cursor": None},
        }

    @router.post("", status_code=201, response_model=ProductEnvelope)
    def create_product(
        body: ProductWrite,
        request: Request,
        response: Response,
        environment: str = Query(..., min_length=1, max_length=64),
        actor: str = Header(..., alias="X-DataObs-Actor"),
        reason: str = Header(..., alias="X-DataObs-Reason"),
        idempotency_key: str = Header(..., alias="Idempotency-Key", max_length=200),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        product = DataProduct(
            **body.model_dump(),
            tenant_id=request.state.tenant_id,
            environment=environment,
            revision=1,
            etag='"pending"',
        )
        try:
            return envelope(
                application.create(product, actor=actor, reason=reason, idempotency_key=idempotency_key),
                request,
                response,
            )
        except ProductVersionConflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.get("/{product_id}", response_model=ProductEnvelope)
    def get_product(
        product_id: str,
        request: Request,
        response: Response,
        environment: str = Query(...),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        try:
            return envelope(application.get(request.state.tenant_id, environment, product_id), request, response)
        except KeyError as exc:
            raise HTTPException(404, "Data Product not found") from exc

    @router.patch("/{product_id}", response_model=ProductEnvelope)
    def update_product(
        product_id: str,
        body: ProductWrite,
        request: Request,
        response: Response,
        environment: str = Query(...),
        if_match: str = Header(..., alias="If-Match"),
        actor: str = Header(..., alias="X-DataObs-Actor"),
        reason: str = Header(..., alias="X-DataObs-Reason"),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        if body.id != product_id:
            raise HTTPException(422, "Path and body product IDs differ")
        product = DataProduct(
            **body.model_dump(), tenant_id=request.state.tenant_id, environment=environment, etag=if_match
        )
        try:
            return envelope(
                application.update(
                    product, if_match=if_match, actor=actor, reason=reason, idempotency_key=idempotency_key
                ),
                request,
                response,
            )
        except ProductVersionConflict as exc:
            raise HTTPException(412, str(exc)) from exc

    @router.post("/{product_id}/{action}", response_model=ProductEnvelope)
    def transition(
        product_id: str,
        action: Literal["activate", "deprecate", "archive"],
        body: ActionRequest,
        request: Request,
        response: Response,
        environment: str = Query(...),
        if_match: str = Header(..., alias="If-Match"),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        del idempotency_key
        try:
            product = getattr(application, action)(
                request.state.tenant_id,
                environment,
                product_id,
                if_match=if_match,
                actor=body.actor,
                reason=body.reason,
            )
            return envelope(product, request, response)
        except KeyError as exc:
            raise HTTPException(404, "Data Product not found") from exc
        except ProductVersionConflict as exc:
            raise HTTPException(412, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    return router
