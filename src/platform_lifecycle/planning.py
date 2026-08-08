from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from typing import Any

from .models import SHA, state_hash
from .service import LifecycleError


@dataclass(frozen=True)
class DeploymentPlan:
    plan_id: str
    environment_id: str
    state: str
    current_hash: str
    desired_hash: str
    changes: tuple[str, ...]
    migration_required: bool
    restart_required: bool
    downtime_expected: bool
    backup_required: bool
    approval_required: bool
    verification: tuple[str, ...]
    rollback_release_sha: str | None
    revision: int = 1

    def advance(self, target: str) -> "DeploymentPlan":
        transitions = {
            "created": {"validated"},
            "validated": {"approval_required", "executing"},
            "approval_required": {"approved"},
            "approved": {"executing"},
            "executing": {"verifying", "failed"},
            "verifying": {"completed", "failed"},
            "failed": {"rollback_required"},
            "rollback_required": {"rolled_back"},
            "completed": set(),
            "rolled_back": set(),
        }
        if target not in transitions.get(self.state, set()):
            raise LifecycleError("invalid_plan_transition", f"{self.state} cannot transition to {target}", 409)
        return replace(self, state=target, revision=self.revision + 1)


def create_plan(environment_id: str, current: dict[str, Any], desired: dict[str, Any]) -> DeploymentPlan:
    changes = tuple(sorted(key for key in set(current) | set(desired) if current.get(key) != desired.get(key)))
    migration = current.get("terminal_migration") != desired.get("terminal_migration")
    return DeploymentPlan(
        str(uuid.uuid4()),
        environment_id,
        "created",
        state_hash(current),
        state_hash(desired),
        changes,
        migration,
        bool(changes),
        migration,
        migration,
        True,
        ("readiness", "migration", "authentication", "elasticsearch", "telemetry", "critical_alerts", "slo"),
        current.get("release_sha"),
    )


def validate_promotion(evidence: dict[str, Any], production: bool = True) -> dict[str, Any]:
    sha = evidence.get("release_sha", "")
    if not SHA.fullmatch(sha):
        raise LifecycleError("mutable_release_rejected", "promotion requires exact SHA")
    required = [
        "signature_valid",
        "digests_match",
        "source_certified",
        "destination_supported",
        "migration_compatible",
        "backup_ready",
        "security_certified",
        "slo_healthy",
    ]
    unknown = [key for key in required if evidence.get(key) is None]
    failed = [key for key in required if evidence.get(key) is False]
    if unknown:
        raise LifecycleError("mandatory_evidence_unknown", ", ".join(unknown), 409)
    if failed:
        raise LifecycleError("promotion_gate_failed", ", ".join(failed), 409)
    if production and evidence.get("release_decision") != "approved":
        raise LifecycleError("release_not_approved", "production release decision is not approved", 409)
    return {"state": "validated", "release_sha": sha, "strategy": evidence.get("strategy", "rolling")}
