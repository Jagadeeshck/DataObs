from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .catalogue import CATALOGUE, canonical_hash
from .contracts import Approval, ApprovalState, Execution, ExecutionState, Preview
from .policy import POLICY_HASH
from .repository import AutomationRepository, Conflict
from .safe_text import validate_safe_text

MAX_REASON = 500
MAX_IMPACT = 1000
MAX_COMMENT = 1000
RESERVATION_TTL = timedelta(minutes=5)


class Expired(RuntimeError):
    pass


class PolicyDenied(RuntimeError):
    pass


def _event_document(kind: str, item: Approval | Execution, actor: str, request_id: str) -> dict[str, object]:
    return {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": item.tenant_id,
        "environment": item.environment,
        "incident_id": item.incident_id,
        "event_type": kind,
        "action_type": item.action_type,
        "request_id": request_id,
        "correlation_id": item.action_fingerprint,
        "metadata": {"actor": actor, "catalogue_hash": item.catalogue_hash, "policy_hash": item.policy_hash},
    }


class AutomationCoordinator:
    def __init__(self, repository: AutomationRepository) -> None:
        self.repository = repository

    def save_preview(self, preview: Preview) -> Preview:
        saved = self.repository.save_preview(preview)
        self.repository.append_event(
            "remediation_action",
            canonical_hash([saved.preview_id, "previewed"]),
            {
                "@timestamp": saved.previewed_at.isoformat(),
                "tenant_id": saved.tenant_id,
                "environment": saved.environment,
                "incident_id": saved.incident_id,
                "event_type": "action_previewed",
                "action_type": saved.action_type,
                "risk_level": saved.risk.value,
                "request_id": saved.request_id,
                "correlation_id": saved.action_fingerprint,
                "metadata": {"catalogue_hash": saved.catalogue_hash, "policy_hash": saved.policy_hash},
            },
        )
        return saved

    def request_approval(
        self,
        preview: Preview,
        *,
        requester: str,
        idempotency_key: str,
        reason: str,
        impact: str,
        now: datetime | None = None,
    ) -> Approval:
        checked = now or datetime.now(timezone.utc)
        if checked >= preview.expires_at:
            raise Expired("preview expired")
        if not preview.approval_required:
            raise ValueError("this action does not require approval")
        validate_safe_text(reason, field="approval reason", maximum=MAX_REASON)
        validate_safe_text(impact, field="approval impact", maximum=MAX_IMPACT)
        approval_id = "apr_" + canonical_hash(
            {
                "tenant": preview.tenant_id,
                "environment": preview.environment,
                "preview": preview.preview_id,
                "key": idempotency_key,
            }
        )
        approval = Approval(
            approval_id=approval_id,
            tenant_id=preview.tenant_id,
            environment=preview.environment,
            incident_id=preview.incident_id,
            incident_revision=preview.incident_revision,
            preview_id=preview.preview_id,
            action_fingerprint=preview.action_fingerprint,
            action_type=preview.action_type,
            action_version=preview.action_version,
            catalogue_hash=preview.catalogue_hash,
            policy_hash=preview.policy_hash,
            risk=preview.risk,
            target=preview.target,
            payload_fingerprint=preview.payload_fingerprint,
            requester=requester,
            required_permission="workflows:approve",
            requested_at=checked,
            expires_at=min(preview.expires_at, checked + timedelta(minutes=30)),
            reason=reason,
            impact=impact,
            request_id=preview.request_id,
        )
        saved = self.repository.create_approval(approval)
        self.repository.append_event(
            "approval_event",
            canonical_hash([approval_id, "requested"]),
            _event_document("approval_requested", saved, requester, preview.request_id),
        )
        return saved

    def decide_approval(
        self,
        tenant_id: str,
        environment: str,
        approval_id: str,
        *,
        actor: str,
        permissions: set[str],
        approve: bool,
        comment: str,
        request_id: str,
        now: datetime | None = None,
    ) -> Approval:
        approval = self.repository.get_approval(tenant_id, environment, approval_id)
        if not approval:
            raise KeyError(approval_id)
        checked = now or datetime.now(timezone.utc)
        kind = "approval_approved" if approve else "approval_rejected"
        event_id = canonical_hash([approval_id, kind, request_id])
        desired_state = ApprovalState.APPROVED if approve else ApprovalState.REJECTED
        if approval.state != ApprovalState.REQUESTED:
            if (
                approval.state == desired_state
                and approval.decided_by == actor
                and approval.decision_request_id == request_id
            ):
                self._deliver_decision_event(approval)
                return self.repository.get_approval(tenant_id, environment, approval_id) or approval
            raise Conflict("approval is no longer pending")
        if checked >= approval.expires_at:
            old = approval.revision
            approval.state = ApprovalState.EXPIRED
            saved = self.repository.update_approval(approval, old)
            self.repository.append_event(
                "approval_event",
                canonical_hash([approval_id, "expired"]),
                _event_document("approval_expired", saved, actor, request_id),
            )
            raise Expired("approval expired")
        if actor == approval.requester:
            raise PermissionError("requester cannot approve their own governed action")
        if approval.required_permission not in permissions:
            raise PermissionError("approval decision permission required")
        validate_safe_text(comment, field="approval comment", maximum=MAX_COMMENT, allow_empty=True)
        old = approval.revision
        approval.state = desired_state
        approval.decided_by = actor
        approval.decision_comment = comment
        approval.decision_request_id = request_id
        approval.decision_event_id = event_id
        approval.decision_event_type = kind
        approval.decision_event_pending = True
        saved = self.repository.update_approval(approval, old)
        self._deliver_decision_event(saved)
        return self.repository.get_approval(tenant_id, environment, approval_id) or saved

    def _deliver_decision_event(self, approval: Approval) -> None:
        if not approval.decision_event_pending or not approval.decision_event_id or not approval.decision_event_type:
            return
        self.repository.append_event(
            "approval_event",
            approval.decision_event_id,
            _event_document(
                approval.decision_event_type,
                approval,
                approval.decided_by or "unknown",
                approval.decision_request_id or approval.request_id,
            ),
        )
        old = approval.revision
        approval.decision_event_pending = False
        self.repository.update_approval(approval, old)

    def queue_execution(
        self,
        preview: Preview,
        *,
        actor: str,
        idempotency_key: str,
        current_incident_revision: str,
        current_target_revision: str,
        approval_id: str | None,
        request_id: str,
        now: datetime | None = None,
    ) -> Execution:
        checked = now or datetime.now(timezone.utc)
        if checked >= preview.expires_at:
            raise Expired("preview expired")
        if not preview.allowed:
            if preview.provider_state == "not_configured":
                raise PolicyDenied("executor not configured")
            raise PolicyDenied(preview.denial_reason or "action denied")
        if actor != preview.actor:
            raise Conflict("preview actor changed; create a new preview")
        if preview.catalogue_hash != CATALOGUE.hash or preview.policy_hash != POLICY_HASH:
            raise Conflict("catalogue or policy changed; create a new preview")
        if (
            preview.incident_revision != current_incident_revision
            or preview.target["revision"] != current_target_revision
        ):
            raise Conflict("incident or target revision changed")
        approval = None
        if preview.approval_required:
            if not approval_id:
                raise PolicyDenied("approval required")
            approval = self.repository.get_approval(preview.tenant_id, preview.environment, approval_id)
            if not approval:
                raise PolicyDenied("valid approval required")
            if approval.state == ApprovalState.CONSUMED and approval.reserved_execution_id:
                existing = self.repository.get_execution(
                    preview.tenant_id, preview.environment, approval.reserved_execution_id
                )
                if existing and existing.actor == actor and existing.preview_id == preview.preview_id:
                    return existing
                raise PolicyDenied("valid approval required")
            if approval.state not in {ApprovalState.APPROVED, ApprovalState.RESERVED}:
                raise PolicyDenied("valid approval required")
            if checked >= approval.expires_at:
                if approval.state == ApprovalState.APPROVED:
                    self.expire_approval(approval, actor=actor, request_id=request_id, now=checked)
                raise Expired("approval expired")
            if approval.action_fingerprint != preview.action_fingerprint or approval.preview_id != preview.preview_id:
                raise Conflict("approval does not bind to this exact action")
            if approval.decided_by == actor:
                raise PermissionError("approver cannot execute their own governed request")
        operation_identity = {
            "tenant": preview.tenant_id,
            "environment": preview.environment,
            "incident": preview.incident_id,
            "action": preview.action_fingerprint,
            "idempotency_key": idempotency_key if approval is None else approval.approval_id,
        }
        execution_id = "exe_" + canonical_hash(operation_identity)
        idempotency_fingerprint = canonical_hash(
            {
                **operation_identity,
                "preview": preview.preview_id,
                "approval": approval_id,
                "payload": preview.payload_fingerprint,
                "target": preview.target,
            }
        )
        if approval:
            if approval.state == ApprovalState.RESERVED:
                if approval.reserved_execution_id != execution_id or approval.reserved_by != actor:
                    raise Conflict("approval is reserved for another execution")
                existing = self.repository.get_execution(preview.tenant_id, preview.environment, execution_id)
                if existing:
                    self.consume_reservation(approval)
                    return existing
            else:
                old = approval.revision
                approval.state = ApprovalState.RESERVED
                approval.reserved_execution_id = execution_id
                approval.reserved_by = actor
                approval.reserved_at = checked
                approval.reservation_expires_at = checked + RESERVATION_TTL
                approval.reservation_request_id = request_id
                approval = self.repository.update_approval(approval, old)
        definition = CATALOGUE.require(preview.action_type)
        execution = Execution(
            execution_id=execution_id,
            tenant_id=preview.tenant_id,
            environment=preview.environment,
            incident_id=preview.incident_id,
            incident_revision=preview.incident_revision,
            preview_id=preview.preview_id,
            approval_id=approval_id,
            action_type=preview.action_type,
            action_fingerprint=preview.action_fingerprint,
            payload_fingerprint=preview.payload_fingerprint,
            catalogue_hash=preview.catalogue_hash,
            policy_hash=preview.policy_hash,
            target=preview.target,
            actor=actor,
            request_id=request_id,
            state=ExecutionState.QUEUED,
            created_at=checked,
            queued_at=checked,
            updated_at=checked,
            timeout_seconds=definition.timeout_seconds,
            max_attempts=definition.max_attempts,
        )
        saved = self.repository.create_execution(execution, idempotency_fingerprint)
        if approval:
            self.consume_reservation(approval)
        self.repository.append_event(
            "remediation_action",
            canonical_hash([execution_id, "queued"]),
            _event_document("execution_queued", saved, actor, request_id),
        )
        return saved

    def consume_reservation(self, approval: Approval) -> Approval:
        if approval.state == ApprovalState.CONSUMED:
            return approval
        if approval.state != ApprovalState.RESERVED or not approval.reserved_execution_id:
            raise Conflict("approval reservation is invalid")
        if not self.repository.get_execution(approval.tenant_id, approval.environment, approval.reserved_execution_id):
            raise Conflict("reserved execution has not been published")
        old = approval.revision
        approval.state = ApprovalState.CONSUMED
        return self.repository.update_approval(approval, old)

    def expire_approval(self, approval: Approval, *, actor: str, request_id: str, now: datetime) -> Approval:
        if approval.state != ApprovalState.APPROVED:
            return approval
        old = approval.revision
        approval.state = ApprovalState.EXPIRED
        approval.expired_at = now
        saved = self.repository.update_approval(approval, old)
        self.repository.append_event(
            "approval_event",
            canonical_hash([approval.approval_id, "expired"]),
            _event_document("approval_expired", saved, actor, request_id),
        )
        return saved
