"""Typed HTTP boundary for scoped Data Product workflows."""

from __future__ import annotations

import os
from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from packages.domain_model.data_product import DataProduct, DataProductCriticality, DataProductOutput, DataProductOwner
from services.data_products.cursors import CursorContext, InvalidCursor, SignedCursorCodec
from services.data_products.dependency_service import DataProductDependencyService
from services.data_products.impact import DataProductImpactService
from services.data_products.membership_service import DataProductMembershipService
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


class ManualMembershipRequest(ActionRequest):
    entity_id: str = Field(min_length=1, max_length=256)
    entity_type: Literal["asset", "api", "kafka_topic", "dashboard", "model", "application", "app"]


class ProposalActionRequest(ActionRequest):
    expected_revision: int = Field(ge=1)


class DependencyReplaceRequest(ActionRequest):
    upstream_product_ids: list[str] = Field(default_factory=list, max_length=200)


class ProposalGenerationRequest(BaseModel):
    source: Literal["lineage", "dependency"]
    evidence: list[tuple[str, str, str]] = Field(default_factory=list, max_length=500)
    max_proposals: int = Field(default=100, ge=1, le=200)


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

    def membership_service(repository: Any = Depends(repository_provider)) -> DataProductMembershipService:
        return DataProductMembershipService(repository)

    def dependency_service(repository: Any = Depends(repository_provider)) -> DataProductDependencyService:
        return DataProductDependencyService(repository)

    def impact_service(repository: Any = Depends(repository_provider)) -> DataProductImpactService:
        return DataProductImpactService(repository)

    cursor_codec = SignedCursorCodec(
        os.environ.get("DATAOBS_CURSOR_SECRET", "development-only-cursor-secret-32-bytes").encode()
    )

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
        context = CursorContext("products", request.state.tenant_id, environment, filters)
        try:
            search_after = cursor_codec.decode(cursor, context) if cursor else None
        except InvalidCursor as exc:
            raise HTTPException(422, str(exc)) from exc
        products = list(
            application.repository.list_products(
                request.state.tenant_id,
                environment,
                limit=limit + 1,
                search_after=search_after,
                filters=filters,
            )
        )
        has_more = len(products) > limit
        products = products[:limit]
        next_cursor = (
            cursor_codec.encode(
                context,
                [products[-1].id, f"{request.state.tenant_id}:{environment}:{products[-1].id}"],
            )
            if has_more and products
            else None
        )
        return {
            "items": products,
            "data_status": "available",
            "source_coverage": 1,
            "confidence": 1,
            "warnings": [],
            "request_id": request.state.request_id,
            "trace_id": request.headers.get("traceparent", request.state.request_id),
            "pagination": {"limit": limit, "next_cursor": next_cursor},
        }

    def paged(
        repository: Any,
        method: str,
        request: Request,
        environment: str,
        product_id: str,
        resource: str,
        limit: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        context = CursorContext(resource, request.state.tenant_id, environment, {"product_id": product_id})
        try:
            after = cursor_codec.decode(cursor, context) if cursor else None
        except InvalidCursor as exc:
            raise HTTPException(422, str(exc)) from exc
        page = getattr(repository, method)(
            request.state.tenant_id, environment, product_id, limit=limit, search_after=after
        )
        payload = page.model_dump(mode="json") if hasattr(page, "model_dump") else {"items": page}
        sort_values = payload.pop("search_after", None)
        payload["next_cursor"] = (
            cursor_codec.encode(context, sort_values) if payload.get("has_more") and sort_values else None
        )
        return payload

    @router.get("/{product_id}/revisions")
    def revisions(
        product_id: str,
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        context = CursorContext("revisions", request.state.tenant_id, environment, {"product_id": product_id})
        try:
            after = cursor_codec.decode(cursor, context) if cursor else None
        except InvalidCursor as exc:
            raise HTTPException(422, str(exc)) from exc
        events = application.repository.list_revisions(
            request.state.tenant_id,
            environment,
            product_id,
            limit=limit + 1,
            search_after=after,
        )
        has_more = len(events) > limit
        events = events[:limit]
        next_cursor = None
        if has_more and events:
            last = events[-1]
            next_cursor = cursor_codec.encode(
                context,
                [last.revision, last.occurred_at.isoformat(), last.operation_id, last.operation_id],
            )
        return {"items": events, "has_more": has_more, "next_cursor": next_cursor}

    @router.get("/{product_id}/members")
    def members(
        product_id: str,
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        return paged(
            application.repository, "list_memberships", request, environment, product_id, "members", limit, cursor
        )

    @router.get("/{product_id}/membership-proposals")
    def proposals(
        product_id: str,
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        return paged(
            application.repository,
            "list_membership_proposals",
            request,
            environment,
            product_id,
            "proposals",
            limit,
            cursor,
        )

    @router.get("/{product_id}/membership-decisions")
    def decisions(
        product_id: str,
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        return paged(
            application.repository,
            "list_membership_decisions",
            request,
            environment,
            product_id,
            "decisions",
            limit,
            cursor,
        )

    @router.get("/{product_id}/dependencies")
    def dependencies(
        product_id: str,
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        return paged(
            application.repository, "list_dependencies", request, environment, product_id, "dependencies", limit, cursor
        )

    @router.post("/{product_id}/members", status_code=201)
    def add_member(
        product_id: str,
        body: ManualMembershipRequest,
        request: Request,
        response: Response,
        environment: str = Query(...),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        application: DataProductMembershipService = Depends(membership_service),
    ) -> dict[str, Any]:
        result = application.add_manual_member(
            request.state.tenant_id,
            environment,
            product_id,
            entity_id=body.entity_id,
            entity_type=body.entity_type,
            actor=body.actor,
            reason=body.reason,
            idempotency_key=idempotency_key,
        )
        response.headers["ETag"] = result.membership.etag
        response.headers["Idempotency-Replayed"] = str(result.replayed).lower()
        return {**result.__dict__, "request_id": request.state.request_id}

    @router.post("/{product_id}/members/{membership_id}/exclude")
    def exclude_member(
        product_id: str,
        membership_id: str,
        body: ActionRequest,
        request: Request,
        response: Response,
        environment: str = Query(...),
        if_match: str = Header(..., alias="If-Match"),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        application: DataProductMembershipService = Depends(membership_service),
    ) -> dict[str, Any]:
        result = application.exclude_member(
            request.state.tenant_id,
            environment,
            product_id,
            membership_id,
            actor=body.actor,
            reason=body.reason,
            idempotency_key=idempotency_key,
            expected_etag=if_match,
        )
        response.headers["ETag"] = result.membership.etag
        response.headers["Idempotency-Replayed"] = str(result.replayed).lower()
        return {
            **result.__dict__,
            "request_id": request.state.request_id,
            "trace_id": request.headers.get("traceparent", request.state.request_id),
        }

    @router.post("/{product_id}/membership-proposals/{proposal_id}/{decision}")
    def decide_proposal(
        product_id: str,
        proposal_id: str,
        decision: Literal["accept", "reject", "expire", "supersede"],
        body: ProposalActionRequest,
        request: Request,
        response: Response,
        environment: str = Query(...),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        application: DataProductMembershipService = Depends(membership_service),
    ) -> dict[str, Any]:
        handlers = {
            "accept": application.accept_proposal,
            "reject": application.reject_proposal,
            "expire": application.expire_proposal,
            "supersede": application.supersede_proposal,
        }
        result = handlers[decision](
            request.state.tenant_id,
            environment,
            product_id,
            proposal_id,
            actor=body.actor,
            reason=body.reason,
            idempotency_key=idempotency_key,
            expected_revision=body.expected_revision,
        )
        response.headers["Idempotency-Replayed"] = str(result.replayed).lower()
        return {
            **result.__dict__,
            "request_id": request.state.request_id,
            "trace_id": request.headers.get("traceparent", request.state.request_id),
        }

    @router.post("/{product_id}/membership-proposals/generate")
    def generate_proposals(
        product_id: str,
        body: ProposalGenerationRequest,
        request: Request,
        environment: str = Query(...),
        application: DataProductMembershipService = Depends(membership_service),
    ) -> dict[str, Any]:
        handler = (
            application.generate_lineage_proposals
            if body.source == "lineage"
            else application.generate_dependency_proposals
        )
        return handler(
            request.state.tenant_id,
            environment,
            product_id,
            evidence=body.evidence,
            max_proposals=body.max_proposals,
        ).model_dump(mode="json")

    @router.put("/{product_id}/dependencies")
    def replace_dependencies(
        product_id: str,
        body: DependencyReplaceRequest,
        request: Request,
        environment: str = Query(...),
        if_match: str = Header(..., alias="If-Match"),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        application: DataProductDependencyService = Depends(dependency_service),
    ) -> dict[str, Any]:
        page = application.replace_declared_dependencies(
            request.state.tenant_id,
            environment,
            product_id,
            body.upstream_product_ids,
            expected_etag=if_match,
            actor=body.actor,
            reason=body.reason,
            idempotency_key=idempotency_key,
        )
        return page.model_dump(mode="json")

    @router.get("/{product_id}/dependencies/{direction}")
    def traverse_dependencies(
        product_id: str,
        direction: Literal["upstream", "downstream"],
        request: Request,
        environment: str = Query(...),
        depth: int = Query(1, ge=1, le=32),
        max_nodes: int = Query(200, ge=1, le=1000),
        application: DataProductService = Depends(service),
    ) -> dict[str, Any]:
        repository = application.repository
        graph = (
            repository.get_direct_upstream
            if direction == "upstream" and depth == 1
            else (
                repository.get_direct_downstream
                if direction == "downstream" and depth == 1
                else (
                    repository.get_transitive_upstream
                    if direction == "upstream"
                    else repository.get_transitive_downstream
                )
            )
        )(
            request.state.tenant_id,
            environment,
            product_id,
            max_nodes=max_nodes,
            **({"max_depth": depth} if depth > 1 else {}),
        )
        return graph.model_dump(mode="json")

    @router.get("/{product_id}/impact")
    def impact(
        product_id: str,
        request: Request,
        environment: str = Query(...),
        limit: int = Query(200, ge=1, le=1000),
        application: DataProductImpactService = Depends(impact_service),
    ) -> dict[str, Any]:
        return application.summarize(request.state.tenant_id, environment, product_id, limit=limit).model_dump(
            mode="json"
        )

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
        try:
            product = getattr(application, action)(
                request.state.tenant_id,
                environment,
                product_id,
                if_match=if_match,
                actor=body.actor,
                reason=body.reason,
                idempotency_key=idempotency_key,
            )
            return envelope(product, request, response)
        except KeyError as exc:
            raise HTTPException(404, "Data Product not found") from exc
        except ProductVersionConflict as exc:
            raise HTTPException(412, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    return router
