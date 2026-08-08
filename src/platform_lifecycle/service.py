from __future__ import annotations

import builtins
import re
import uuid
from dataclasses import replace
from typing import Any, cast
from typing import List as TypingList

from .models import (
    SHA,
    Cluster,
    ClusterState,
    Environment,
    EnvironmentState,
    Installation,
    LifecycleEvent,
    Tenant,
    TenantState,
    now,
    safe_id,
    state_hash,
)
from .repository import ConflictError, InMemoryLifecycleRepository


class LifecycleError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.status = code, status


ENV_TRANSITIONS = {
    "requested": {"provisioning", "failed"},
    "provisioning": {"configured", "failed"},
    "configured": {"validating", "failed"},
    "validating": {"ready", "failed"},
    "ready": {"degraded", "maintenance", "upgrade_pending", "retiring"},
    "degraded": {"validating", "maintenance", "rollback_pending", "failed"},
    "maintenance": {"validating", "retiring"},
    "upgrade_pending": {"upgrading"},
    "upgrading": {"validating", "rollback_pending", "failed"},
    "rollback_pending": {"upgrading"},
    "retiring": {"retired"},
    "failed": {"provisioning", "validating"},
    "retired": set(),
}
CLUSTER_TRANSITIONS = {
    "discovered": {"registered"},
    "registered": {"validating", "unregistered"},
    "validating": {"ready", "degraded"},
    "ready": {"degraded", "draining"},
    "degraded": {"validating", "draining"},
    "draining": {"unregistered"},
    "unregistered": set(),
}
TENANT_TRANSITIONS = {
    "requested": {"approved", "failed"},
    "approved": {"provisioning"},
    "provisioning": {"validating", "failed"},
    "validating": {"active", "failed"},
    "active": {"suspended"},
    "suspended": {"active", "offboarding"},
    "offboarding": {"retention_hold", "deleting"},
    "retention_hold": {"offboarding"},
    "deleting": {"deleted", "failed"},
    "failed": {"provisioning"},
    "deleted": set(),
}


class PlatformLifecycleService:
    SUPPORTED_KUBERNETES = re.compile(r"^1\.30(?:\.[0-9]+)?$")
    ISOLATION_PROFILES = {"shared"}

    def __init__(self, repository: InMemoryLifecycleRepository | None = None):
        self.repo = repository or InMemoryLifecycleRepository()
        self.plans: dict[str, Any] = {}

    def _create(self, kind: str, record: Any, key: str, permission: str) -> dict[str, Any]:
        try:
            stored = self.repo.create(kind, record, key)
        except ConflictError as exc:
            raise LifecycleError("duplicate_resource", str(exc), 409) from exc
        self._event(kind, stored, None, stored.state, stored.created_actor, permission, stored.reason_code, key)
        return stored.document()

    def _event(
        self, kind: str, record: Any, old: str | None, new: str, actor: str, permission: str, reason: str, key: str
    ) -> None:
        self.repo.append_event(
            LifecycleEvent(
                str(uuid.uuid4()),
                kind,
                record.id,
                f"{kind}.{new}",
                old,
                new,
                actor,
                permission,
                reason,
                key,
                record.revision,
                now(),
            )
        )

    def create_environment(self, data: dict[str, Any], actor: str, key: str) -> dict[str, Any]:
        try:
            safe_id(data["environment_id"], "environment_id")
        except (KeyError, ValueError) as exc:
            raise LifecycleError("invalid_environment_id", str(exc)) from exc
        desired = data.get("desired_state", {})
        record = Environment(
            id=data["environment_id"],
            state=EnvironmentState.REQUESTED,
            created_actor=actor,
            updated_actor=actor,
            name=data.get("name", data["environment_id"]),
            environment_class=data.get("environment_class", "development"),
            region=data.get("region", ""),
            provider=data.get("provider", "other"),
            elasticsearch_connection_reference=data.get("elasticsearch_connection_reference", ""),
            oidc_configuration_reference=data.get("oidc_configuration_reference", ""),
            desired_state_hash=state_hash(desired),
            configuration_revision=data.get("configuration_revision", "1"),
        )
        return self._create("environment", record, key, "environments:write")

    def register_cluster(self, data: dict[str, Any], actor: str, key: str) -> dict[str, Any]:
        try:
            safe_id(data["cluster_id"], "cluster_id")
        except (KeyError, ValueError) as exc:
            raise LifecycleError("invalid_cluster_id", str(exc)) from exc
        version = data.get("kubernetes_version", "")
        if not self.SUPPORTED_KUBERNETES.fullmatch(version):
            raise LifecycleError("unsupported_kubernetes_version", "cluster is outside the unvalidated 1.30.x profile")
        record = Cluster(
            id=data["cluster_id"],
            state=ClusterState.REGISTERED,
            created_actor=actor,
            updated_actor=actor,
            provider=data.get("provider", "other"),
            region=data.get("region", ""),
            kubernetes_version=version,
            availability_zones=data.get("availability_zones", []),
            capacity_class=data.get("capacity_class", "small"),
            ingress_class=data.get("ingress_class", ""),
            storage_class=data.get("storage_class", ""),
        )
        return self._create("cluster", record, key, "clusters:register")

    def register_installation(self, data: dict[str, Any], actor: str, key: str) -> dict[str, Any]:
        for name in ("installation_id", "cluster_id", "environment_id"):
            try:
                safe_id(data[name], name)
            except (KeyError, ValueError) as exc:
                raise LifecycleError(f"invalid_{name}", str(exc)) from exc
        if not SHA.fullmatch(data.get("release_sha", "")):
            raise LifecycleError("mutable_release_rejected", "release_sha must be an exact 40-character commit SHA")
        self.repo.get("cluster", data["cluster_id"])
        self.repo.get("environment", data["environment_id"])
        record = Installation(
            id=data["installation_id"],
            state="planned",
            created_actor=actor,
            updated_actor=actor,
            cluster_id=data["cluster_id"],
            environment_id=data["environment_id"],
            namespace=safe_id(data["namespace"], "namespace"),
            helm_release_name=safe_id(data["helm_release_name"], "helm_release_name"),
            release_sha=data["release_sha"],
            candidate_version=data.get("candidate_version", ""),
            chart_version=data.get("chart_version", ""),
            image_digests=data.get("image_digests", {}),
            terminal_migration=data.get("terminal_migration", ""),
        )
        return self._create("installation", record, key, "installations:manage")

    def request_tenant(self, data: dict[str, Any], actor: str, key: str) -> dict[str, Any]:
        try:
            safe_id(data["tenant_id"], "tenant_id")
        except (KeyError, ValueError) as exc:
            raise LifecycleError("invalid_tenant_id", str(exc)) from exc
        if data.get("isolation_profile", "shared") not in self.ISOLATION_PROFILES:
            raise LifecycleError("unsupported_isolation_profile", "only tested shared logical isolation is implemented")
        if not data.get("initial_administrators"):
            raise LifecycleError("initial_administrator_required", "at least one external identity binding is required")
        env_id = data.get("requested_environment", "")
        env = cast(Environment, self.repo.get("environment", env_id))
        if data.get("region_requirements") and env.region not in data["region_requirements"]:
            raise LifecycleError("residency_constraint_unsatisfied", "environment region is not eligible")
        record = Tenant(
            id=data["tenant_id"],
            state=TenantState.REQUESTED,
            created_actor=actor,
            updated_actor=actor,
            name=data.get("name", data["tenant_id"]),
            owner=data.get("owner", ""),
            business_reference=data.get("business_reference", ""),
            allowed_environments=data.get("allowed_environments", [env_id]),
            region_requirements=data.get("region_requirements", []),
            residency=data.get("residency", ""),
            data_classification=data.get("data_classification", "internal"),
            retention_profile=data.get("retention_profile", "default"),
            capacity_profile=data.get("capacity_profile", "small"),
            integration_profile=data.get("integration_profile", "default"),
            requested_environment=env_id,
            change_reference=data.get("change_reference", ""),
            isolation_profile=data.get("isolation_profile", "shared"),
            initial_administrators=data["initial_administrators"],
        )
        return self._create("tenant", record, key, "tenants:provision")

    def transition(
        self,
        kind: str,
        record_id: str,
        target: str,
        actor: str,
        permission: str,
        reason: str,
        expected_revision: int,
        key: str,
    ) -> dict[str, Any]:
        transitions = {"environment": ENV_TRANSITIONS, "cluster": CLUSTER_TRANSITIONS, "tenant": TENANT_TRANSITIONS}[
            kind
        ]
        record = self.repo.get(kind, record_id)
        if record.state == target:
            return record.document()
        if target not in transitions.get(record.state, set()):
            raise LifecycleError("invalid_state_transition", f"{record.state} cannot transition to {target}", 409)
        if kind == "tenant" and target == "deleting":
            tenant = cast(Tenant, record)
            if tenant.retention_hold:
                raise LifecycleError("retention_hold_active", "retention hold blocks deletion", 409)
            if not tenant.backup_verified:
                raise LifecycleError("backup_not_verified", "verified backup is required", 409)
            if not tenant.deletion_approved_by or tenant.deletion_approved_by == actor:
                raise LifecycleError("independent_approval_required", "a different actor must approve deletion", 409)
        changed = replace(
            record,
            state=target,
            updated_actor=actor,
            updated_at=now(),
            revision=record.revision + 1,
            reason_code=reason,
        )
        try:
            saved = self.repo.save(kind, changed, expected_revision)
        except ConflictError as exc:
            raise LifecycleError("revision_conflict", str(exc), 412) from exc
        self._event(kind, saved, record.state, target, actor, permission, reason, key)
        return saved.document()

    def approve_deletion(self, tenant_id: str, approver: str, expected_revision: int) -> dict[str, Any]:
        tenant = cast(Tenant, self.repo.get("tenant", tenant_id))
        if tenant.created_actor == approver:
            raise LifecycleError("self_approval_denied", "requester cannot approve deletion", 403)
        changed = replace(
            tenant,
            deletion_approved_by=approver,
            revision=tenant.revision + 1,
            updated_at=now(),
            updated_actor=approver,
        )
        return self.repo.save("tenant", changed, expected_revision).document()

    def offboarding_preview(self, tenant_id: str) -> dict[str, Any]:
        tenant = cast(Tenant, self.repo.get("tenant", tenant_id))
        blockers = [
            code
            for condition, code in (
                (tenant.retention_hold, "retention_hold"),
                (not tenant.backup_verified, "backup_not_verified"),
                (not tenant.deletion_approved_by, "approval_missing"),
            )
            if condition
        ]
        return {
            "tenant_id": tenant_id,
            "dry_run": True,
            "resources": [
                {"type": "tenant_record", "count": 1},
                {"type": "iam_bindings", "count": len(tenant.initial_administrators)},
                {"type": "tenant_scoped_elasticsearch_documents", "count": "calculated_at_execution"},
            ],
            "retention_constraints": ["retention_hold"] if tenant.retention_hold else [],
            "backup_verified": tenant.backup_verified,
            "active_integrations": "authoritative_evidence_required",
            "service_principals": "authoritative_evidence_required",
            "blockers": blockers,
            "contains_tenant_data": False,
        }

    def list(self, kind: str) -> builtins.list[dict[str, Any]]:
        return [x.document() for x in self.repo.list(kind)]

    def get(self, kind: str, record_id: str) -> dict[str, Any]:
        return self.repo.get(kind, record_id).document()

    def drift(self) -> builtins.list[dict[str, Any]]:
        result: TypingList[dict[str, Any]] = []
        for record in self.repo.list("installation"):
            i = cast(Installation, record)
            categories: list[str] = []
            if i.desired_state_hash != i.observed_state_hash:
                categories.append("configuration_drift")
            if i.desired_replicas != i.observed_replicas:
                categories.append("replica_drift")
            result.append(
                {"installation_id": i.id, "state": "drifted" if categories else "none", "categories": categories}
            )
        return result

    def fleet(self) -> dict[str, Any]:
        items = self.list("installation")
        counts = {s: 0 for s in ("healthy", "degraded", "unhealthy", "unknown", "unsupported")}
        for item in items:
            counts[item.get("readiness_state", "unknown") if item.get("readiness_state") in counts else "unknown"] += 1
        releases = {(i["release_sha"], i["terminal_migration"]) for i in items}
        return {
            "items": items,
            "aggregate": {
                **counts,
                "release_skew": "warning" if len(releases) > 1 else "none",
                "migration_skew": "security-critical" if len({x[1] for x in releases}) > 1 else "none",
                "drift": self.drift(),
            },
        }
