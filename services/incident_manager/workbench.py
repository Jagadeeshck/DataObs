from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from packages.domain_model.incident import Incident, IncidentState
from services.data_products.cursors import CursorContext, InvalidCursor, SignedCursorCodec

from .lifecycle import transition
from .repository import IncidentRepository, VersionConflict
from .workbench_contracts import IncidentInboxFilters

MAX_PAGE_SIZE = 100
SECRET_KEY = re.compile(
    r"(authorization|bearer|token|secret|password|credential|api[_-]?key|connection[_-]?string)", re.I
)


def _safe(value: Any, *, depth: int = 0) -> Any:
    """Return a small evidence projection; secrets and provider documents never cross the API."""
    if depth > 3:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(k)[:80]: "[redacted]" if SECRET_KEY.search(str(k)) else _safe(v, depth=depth + 1)
            for k, v in list(value.items())[:25]
        }
    if isinstance(value, list):
        return [_safe(item, depth=depth + 1) for item in value[:25]]
    if isinstance(value, str):
        return value[:500]
    return value


def _fingerprint(context: dict[str, Any]) -> str:
    raw = json.dumps(context, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


class CursorMismatch(ValueError):
    pass


class IncidentWorkbenchService:
    def __init__(self, repository: IncidentRepository) -> None:
        self.repo = repository
        self.cursor_codec = SignedCursorCodec(
            os.environ.get("DATAOBS_CURSOR_SECRET", "development-only-cursor-secret-32-bytes").encode()
        )

    def inbox(
        self,
        tenant_id: str,
        environment: str,
        *,
        filters: dict[str, Any],
        sort: str,
        page_size: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        typed_filters = IncidentInboxFilters.from_dict(filters)
        context = CursorContext(
            "incident-inbox",
            tenant_id,
            environment,
            {"filters": typed_filters.fingerprint_value(), "sort": sort, "page_size": page_size},
        )
        search_after = None
        pit_id = None
        if cursor:
            try:
                values = self.cursor_codec.decode(cursor, context)
                if len(values) < 2 or not isinstance(values[0], str):
                    raise InvalidCursor("cursor sort values are invalid")
                pit_id, search_after = values[0], values[1:]
            except InvalidCursor as exc:
                raise CursorMismatch("invalid incident cursor") from exc
        page = self.repo.search_incidents(tenant_id, environment, typed_filters, sort, page_size, search_after, pit_id)
        return {
            "items": [self._summary(item) for item in page.items],
            "next_cursor": (
                self.cursor_codec.encode(context, [page.pit_id, *page.sort_values]) if page.sort_values else None
            ),
            "data_status": "available",
            "warnings": [],
        }

    @staticmethod
    def _matches(item: Incident, f: dict[str, Any]) -> bool:
        text = f.get("search", "").casefold()
        return (
            (not f.get("state") or str(item.incident_state) == f["state"])
            and (not f.get("severity") or str(item.severity) == f["severity"])
            and (not f.get("owner") or item.owner_team == f["owner"])
            and (not f.get("business_service") or item.business_service == f["business_service"])
            and (not f.get("asset") or f["asset"] in item.affected_assets)
            and (not f.get("unassigned") or not item.owner_team)
            and (
                not text or text in " ".join([item.title, item.impact_summary or "", *item.affected_assets]).casefold()
            )
        )

    @staticmethod
    def _summary(item: Incident) -> dict[str, Any]:
        return {
            "id": item.id,
            "title": item.title,
            "state": str(item.incident_state),
            "severity": str(item.severity),
            "owner": item.owner_team,
            "business_service": item.business_service,
            "affected_assets": item.affected_assets[:5],
            "affected_asset_count": len(item.affected_assets),
            "occurrence_count": item.occurrence_count,
            "opened_at": item.opened_at,
            "last_observed_at": item.last_observed_at,
            "data_status": "available" if item.most_recent_evidence else "unknown",
        }

    def detail(self, tenant_id: str, environment: str, incident_id: str, request_id: str) -> dict[str, Any]:
        item = self.repo.get_incident(tenant_id, incident_id, environment)
        if not item:
            raise KeyError(incident_id)
        evidence = _safe(item.most_recent_evidence)
        missing = [] if evidence else ["latest_evidence"]
        return {
            **self._summary(item),
            "severity_factors": _safe(item.severity_factors),
            "impact_summary": item.impact_summary,
            "first_observed_at": item.first_observed_at,
            "finding_references": item.finding_ids[:100],
            "latest_evidence": evidence,
            "correlation_key": item.correlation_key,
            "revision": f"{item.seq_no}:{item.primary_term}",
            "evidence_coverage": "complete" if evidence else "unknown",
            "warnings": ["No safe evidence is available"] if missing else [],
            "missing_inputs": missing,
            "request_id": request_id,
        }

    def mutate(
        self,
        tenant_id: str,
        environment: str,
        incident_id: str,
        *,
        revision: str,
        actor: str,
        request_id: str,
        state: IncidentState | None = None,
        reason: str | None = None,
        owner: str | None = None,
        comment: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not idempotency_key or len(idempotency_key) > 200:
            # Preserve stale-revision precedence for callers that have not supplied a key.
            missing_key = True
        else:
            missing_key = False
        operation_id = (
            "incident-operation-"
            + hashlib.sha256(f"{tenant_id}:{environment}:{incident_id}:{idempotency_key}".encode()).hexdigest()[:24]
        )
        operation_fingerprint = _fingerprint(
            {
                "tenant": tenant_id,
                "environment": environment,
                "incident": incident_id,
                "revision": revision,
                "state": str(state) if state else None,
                "reason": reason,
                "owner": owner,
                "comment": comment,
                "actor": actor,
            }
        )
        if not missing_key:
            existing = self.repo.get_operation(operation_id)
            if existing:
                if existing["fingerprint"] != operation_fingerprint:
                    raise VersionConflict("idempotency key was used for another operation")
                self.repo.append_event(existing["event"])
                return self.detail(tenant_id, environment, incident_id, request_id)
        item = self.repo.get_incident(tenant_id, incident_id, environment)
        if not item:
            raise KeyError(incident_id)
        if revision != f"{item.seq_no}:{item.primary_term}":
            raise VersionConflict("incident revision is stale")
        event_type, summary = "comment_added", (comment or "")[:500]
        if state is not None:
            before = str(item.incident_state)
            item = transition(item, state, reason=reason)
            event_type, summary = "state_changed", f"State changed from {before} to {state.value}"
        elif owner is not None:
            item.owner_team = owner or None
            event_type, summary = "assignment_changed", "Incident assignment changed"
        elif not comment or not comment.strip():
            raise ValueError("comment is required")
        if missing_key:
            raise ValueError("Idempotency-Key is required and must be at most 200 characters")
        if state is not None or owner is not None:
            item = self.repo.update_incident(item)
        event_id = (
            "incident-event-"
            + hashlib.sha256(f"{tenant_id}:{environment}:{incident_id}:{idempotency_key}".encode()).hexdigest()[:24]
        )
        event = {
            "tenant_id": tenant_id,
            "environment": environment,
            "incident_id": incident_id,
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "summary": summary,
            "revision": int(item.seq_no or 0),
            "request_id": request_id,
        }
        self.repo.save_operation(operation_id, operation_fingerprint, event)
        self.repo.append_event(event)
        return self.detail(tenant_id, environment, incident_id, request_id)

    def timeline(
        self, tenant_id: str, environment: str, incident_id: str, *, page_size: int = 50, cursor: str | None = None
    ) -> dict[str, Any]:
        if not self.repo.get_incident(tenant_id, incident_id, environment):
            raise KeyError(incident_id)
        context = CursorContext(
            "incident-timeline", tenant_id, environment, {"incident_id": incident_id, "page_size": page_size}
        )
        try:
            search_after = self.cursor_codec.decode(cursor, context) if cursor else None
        except InvalidCursor as exc:
            raise CursorMismatch("invalid timeline cursor") from exc
        page = self.repo.search_events(tenant_id, environment, incident_id, page_size, search_after)
        return {
            "items": page.items,
            "next_cursor": self.cursor_codec.encode(context, page.sort_values) if page.sort_values else None,
        }

    def preview(
        self, tenant_id: str, environment: str, incident_id: str, action_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.repo.get_incident(tenant_id, incident_id, environment):
            raise KeyError(incident_id)
        from .service import SAFE_ACTIONS

        allowed = action_type in SAFE_ACTIONS
        return {
            "action_type": action_type,
            "allowed": allowed,
            "denial_reason": None if allowed else "Action is not allowlisted",
            "risk": "low",
            "required_approval_state": "not_required",
            "expected_changes": [],
            "affected_target": incident_id,
            "provider_state": "not_configured" if allowed else "unsupported",
            "warnings": ["Preview only: no executor is configured"],
            "payload_keys": sorted(k for k in payload if not SECRET_KEY.search(k)),
        }
