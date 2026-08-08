from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .catalogue import CATALOGUE, CATALOGUE_NAME, CATALOGUE_VERSION, ActionCatalogue, canonical_hash
from .contracts import Preview
from .policy import POLICY_HASH, POLICY_VERSION, evaluate

PREVIEW_TTL = timedelta(minutes=15)


class PreviewService:
    def __init__(self, catalogue: ActionCatalogue = CATALOGUE) -> None:
        self.catalogue = catalogue

    def create(
        self,
        *,
        tenant_id: str,
        environment: str,
        incident_id: str,
        incident_revision: str,
        incident_state: str,
        severity: str,
        affected_asset_count: int,
        action_type: str,
        payload: dict[str, Any],
        actor: str,
        request_id: str,
        now: datetime | None = None,
        provider_ready: bool = False,
    ) -> Preview:
        definition = self.catalogue.require(action_type)
        normalized = definition.payload_model.model_validate(payload).model_dump(mode="json")
        payload_hash = canonical_hash(normalized)
        identity = {
            "tenant": tenant_id,
            "environment": environment,
            "incident": incident_id,
            "incident_revision": incident_revision,
            "action_type": action_type,
            "action_version": definition.action_version,
            "catalogue_hash": self.catalogue.hash,
            "payload": normalized,
            "actor": actor,
            "target_revision": normalized["target_revision"],
        }
        preview_id = f"prv_{canonical_hash(identity)}"
        action_fingerprint = canonical_hash({**identity, "preview_id": preview_id, "policy_hash": POLICY_HASH})
        decision = evaluate(
            definition,
            environment=environment,
            severity=severity,
            incident_state=incident_state,
            affected_asset_count=affected_asset_count,
            provider_ready=provider_ready,
        )
        checked_at = now or datetime.now(timezone.utc)
        return Preview(
            preview_id=preview_id,
            action_type=action_type,
            action_version=definition.action_version,
            catalogue_name=CATALOGUE_NAME,
            catalogue_version=CATALOGUE_VERSION,
            catalogue_hash=self.catalogue.hash,
            policy_version=POLICY_VERSION,
            policy_hash=POLICY_HASH,
            target={
                "type": definition.target_type,
                "id": normalized["target_id"],
                "revision": normalized["target_revision"],
            },
            risk=decision.risk,
            allowed=decision.allowed,
            policy_decision=decision.reason_code,
            denial_reason=None if decision.allowed else decision.reason_code,
            approval_required=decision.approval_required,
            expected_changes=(f"Create one bounded {action_type} operation",),
            expected_side_effects=("No incident lifecycle state change",),
            timeout_seconds=definition.timeout_seconds,
            retry_policy={"max_attempts": definition.max_attempts},
            verification_plan=definition.verification_strategy,
            rollback_description=definition.rollback_description,
            provider_state="ready" if provider_ready and definition.execution_enabled else "not_configured",
            warnings=("Preview only; no action has run.",),
            missing_inputs=(),
            tenant_id=tenant_id,
            environment=environment,
            incident_id=incident_id,
            incident_revision=incident_revision,
            actor=actor,
            previewed_at=checked_at,
            expires_at=checked_at + PREVIEW_TTL,
            payload_fingerprint=payload_hash,
            action_fingerprint=action_fingerprint,
            request_id=request_id,
        )
