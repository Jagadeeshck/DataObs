from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from packages.domain_model.incident import Incident, IncidentState

from .lifecycle import transition
from .repository import IncidentRepository, VersionConflict

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


def _cursor(index: int, fingerprint: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"i": index, "q": fingerprint}, separators=(",", ":")).encode()).decode()


class CursorMismatch(ValueError):
    pass


class IncidentWorkbenchService:
    def __init__(self, repository: IncidentRepository) -> None:
        self.repo = repository

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
        context = {"tenant": tenant_id, "environment": environment, "filters": filters, "sort": sort, "size": page_size}
        fingerprint = _fingerprint(context)
        start = 0
        if cursor:
            try:
                decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if decoded["q"] != fingerprint:
                    raise CursorMismatch("cursor does not match the current incident query")
                start = int(decoded["i"])
            except CursorMismatch:
                raise
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise CursorMismatch("invalid incident cursor") from exc
        items = self.repo.list_incidents(tenant_id, environment)
        items = [item for item in items if self._matches(item, filters)]
        reverse = sort != "severity"
        keys = {
            "newest_opened": lambda i: (i.opened_at or datetime.min.replace(tzinfo=timezone.utc), i.id),
            "recently_observed": lambda i: (i.last_observed_at or datetime.min.replace(tzinfo=timezone.utc), i.id),
            "occurrence_count": lambda i: (i.occurrence_count, i.id),
            "severity": lambda i: ({"critical": 0, "high": 1, "medium": 2, "low": 3}[str(i.severity)], i.id),
        }
        items.sort(key=keys.get(sort, keys["recently_observed"]), reverse=reverse)
        page = items[start : start + page_size]
        return {
            "items": [self._summary(item) for item in page],
            "next_cursor": _cursor(start + len(page), fingerprint) if start + len(page) < len(items) else None,
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
        if state is not None or owner is not None:
            item = self.repo.update_incident(item)
        event_id = (
            "incident-event-"
            + hashlib.sha256(f"{tenant_id}:{incident_id}:{idempotency_key or uuid.uuid4()}".encode()).hexdigest()[:24]
        )
        self.repo.append_event(
            {
                "tenant_id": tenant_id,
                "environment": environment,
                "incident_id": incident_id,
                "event_id": event_id,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "summary": summary,
                "revision": f"{item.seq_no}:{item.primary_term}",
                "request_id": request_id,
            }
        )
        return self.detail(tenant_id, environment, incident_id, request_id)

    def timeline(self, tenant_id: str, environment: str, incident_id: str) -> dict[str, Any]:
        if not self.repo.get_incident(tenant_id, incident_id, environment):
            raise KeyError(incident_id)
        return {"items": self.repo.list_events(tenant_id, environment, incident_id), "next_cursor": None}

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
