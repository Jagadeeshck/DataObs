from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from src.platform_lifecycle import LifecycleError, PlatformLifecycleService
from src.platform_lifecycle.planning import create_plan, validate_promotion
from src.platform_lifecycle.compatibility import PlatformProfile, assess_upgrade, load_policy
from scripts.release.current_terminal_migration import migration_report


def create_platform_lifecycle_router(require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/platform", tags=["platform-lifecycle"], dependencies=[Depends(require_auth)])

    def service(request: Request) -> PlatformLifecycleService:
        return request.app.state.platform_lifecycle_service

    def actor(request: Request) -> str:
        return request.state.principal.subject

    def revision(if_match: str | None) -> int:
        if not if_match:
            raise HTTPException(428, detail={"code": "if_match_required", "message": "If-Match is required"})
        try:
            return int(if_match.removeprefix('W/"').removesuffix('"'))
        except ValueError as exc:
            raise HTTPException(400, detail={"code": "invalid_etag", "message": "Malformed If-Match"}) from exc

    def invoke(call: Callable[[], Any]) -> Any:
        try:
            return call()
        except LifecycleError as exc:
            raise HTTPException(exc.status, detail={"code": exc.code, "message": str(exc)}) from exc
        except KeyError as exc:
            raise HTTPException(404, detail={"code": "not_found", "message": str(exc)}) from exc
        except ValueError as exc:
            raise HTTPException(422, detail={"code": "invalid_request", "message": str(exc)}) from exc

    @router.post("/environments", status_code=201)
    def create_environment(
        payload: dict[str, Any],
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        lifecycle=Depends(service),
    ):
        return invoke(lambda: lifecycle.create_environment(payload, actor(request), idempotency_key))

    @router.get("/environments")
    def environments(lifecycle=Depends(service)):
        return {"items": lifecycle.list("environment")}

    @router.get("/environments/{environment_id}")
    def environment(environment_id: str, lifecycle=Depends(service)):
        return invoke(lambda: lifecycle.get("environment", environment_id))

    @router.post("/environments/{environment_id}/transition")
    def transition_environment(
        environment_id: str,
        payload: dict[str, Any],
        request: Request,
        if_match: str | None = Header(None, alias="If-Match"),
        idempotency_key: str = Header(alias="Idempotency-Key"),
        lifecycle=Depends(service),
    ):
        return invoke(
            lambda: lifecycle.transition(
                "environment",
                environment_id,
                payload["target_state"],
                actor(request),
                "environments:write",
                payload.get("reason_code", "operator_requested"),
                revision(if_match),
                idempotency_key,
            )
        )

    @router.post("/clusters/register", status_code=201)
    def register_cluster(
        payload: dict[str, Any],
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        lifecycle=Depends(service),
    ):
        return invoke(lambda: lifecycle.register_cluster(payload, actor(request), idempotency_key))

    @router.get("/clusters")
    def clusters(lifecycle=Depends(service)):
        return {"items": lifecycle.list("cluster")}

    @router.get("/clusters/{cluster_id}")
    def cluster(cluster_id: str, lifecycle=Depends(service)):
        return invoke(lambda: lifecycle.get("cluster", cluster_id))

    @router.post("/installations", status_code=201)
    def register_installation(
        payload: dict[str, Any],
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        lifecycle=Depends(service),
    ):
        return invoke(lambda: lifecycle.register_installation(payload, actor(request), idempotency_key))

    @router.get("/installations")
    def installations(lifecycle=Depends(service)):
        return {"items": lifecycle.list("installation")}

    @router.get("/installations/{installation_id}")
    def installation(installation_id: str, lifecycle=Depends(service)):
        return invoke(lambda: lifecycle.get("installation", installation_id))

    @router.post("/tenants", status_code=201)
    def request_tenant(
        payload: dict[str, Any],
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        lifecycle=Depends(service),
    ):
        return invoke(lambda: lifecycle.request_tenant(payload, actor(request), idempotency_key))

    @router.get("/tenants")
    def tenants(lifecycle=Depends(service)):
        return {"items": lifecycle.list("tenant")}

    @router.get("/tenants/{tenant_id}")
    def tenant(tenant_id: str, lifecycle=Depends(service)):
        return invoke(lambda: lifecycle.get("tenant", tenant_id))

    @router.post("/tenants/{tenant_id}/{action}")
    def tenant_action(
        tenant_id: str,
        action: str,
        payload: dict[str, Any],
        request: Request,
        if_match: str | None = Header(None, alias="If-Match"),
        idempotency_key: str = Header(alias="Idempotency-Key"),
        lifecycle=Depends(service),
    ):
        targets = {
            "approve": "approved",
            "provision": "provisioning",
            "validate": "validating",
            "activate": "active",
            "suspend": "suspended",
            "resume": "active",
            "offboard": "offboarding",
            "delete": "deleting",
            "verify-deletion": "deleted",
        }
        if action == "approve-deletion":
            return invoke(lambda: lifecycle.approve_deletion(tenant_id, actor(request), revision(if_match)))
        if action not in targets:
            raise HTTPException(404, detail={"code": "action_not_found"})
        permission = (
            "tenants:offboard"
            if action in {"offboard", "delete", "verify-deletion"}
            else ("tenants:suspend" if action in {"suspend", "resume"} else "tenants:provision")
        )
        return invoke(
            lambda: lifecycle.transition(
                "tenant",
                tenant_id,
                targets[action],
                actor(request),
                permission,
                payload.get("reason_code", action),
                revision(if_match),
                idempotency_key,
            )
        )

    @router.get("/tenants/{tenant_id}/offboarding-preview")
    def preview(tenant_id: str, lifecycle=Depends(service)):
        return invoke(lambda: lifecycle.offboarding_preview(tenant_id))

    @router.get("/fleet")
    def fleet(lifecycle=Depends(service)):
        return lifecycle.fleet()

    @router.get("/drift")
    def drift(lifecycle=Depends(service)):
        return {"items": lifecycle.drift()}

    @router.get("/capacity")
    def capacity():
        return {"profiles_reference": "docs/operations/platform-capacity-profiles.yaml", "state": "unvalidated"}

    @router.get("/compatibility")
    def compatibility():
        matrix = load_policy()
        return {"dataobs_version": matrix["dataobs_version"], "release_state": matrix["release_state"], "dimensions": matrix["dimensions"]}

    @router.get("/upgrade-readiness")
    def upgrade_readiness(target: str):
        matrix=load_policy(); terminal=migration_report()["terminal_migration"]
        current=PlatformProfile(matrix["dataobs_version"],"3.17.0","1.30.0","9.4.2","3.13.0","22.0.0","dataobs-oidc-v1","1.0.0","1.0.0","1",terminal)
        desired=PlatformProfile(target,"3.17.0","1.30.0","9.4.2","3.13.0","22.0.0","dataobs-oidc-v1","1.0.0","1.0.0","1",terminal)
        result=assess_upgrade(current,desired,{})
        return {"current":current.dataobs,"target":target,"readiness":result.state,"reason_codes":result.reason_codes,"rollback_classification":result.rollback,"plan":result.plan}

    @router.post("/deployment-plans", status_code=201)
    def deployment_plan(payload: dict[str, Any], lifecycle=Depends(service)):
        plan = create_plan(payload["environment_id"], payload.get("current", {}), payload["desired"])
        lifecycle.plans[plan.plan_id] = plan
        return plan.__dict__

    @router.post("/deployment-plans/{plan_id}/transition")
    def transition_plan(plan_id: str, payload: dict[str, Any], lifecycle=Depends(service)):
        if plan_id not in lifecycle.plans:
            raise HTTPException(404, detail={"code": "plan_not_found"})
        plan = invoke(lambda: lifecycle.plans[plan_id].advance(payload["target_state"]))
        lifecycle.plans[plan_id] = plan
        return plan.__dict__

    @router.post("/promotions", status_code=201)
    def promotion(payload: dict[str, Any]):
        return invoke(lambda: validate_promotion(payload, payload.get("destination_class") == "production"))

    return router
