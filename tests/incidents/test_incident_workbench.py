from datetime import datetime, timezone

import pytest

from packages.domain_model.incident import Incident, IncidentState, Severity
from services.incident_manager.repository import InMemoryIncidentRepository, VersionConflict
from services.incident_manager.workbench import CursorMismatch, IncidentWorkbenchService


def incident(identifier="i1", tenant="t1", environment="prod", **kwargs):
    return Incident(
        id=identifier,
        tenant_id=tenant,
        environment=environment,
        deduplication_key=identifier,
        title=kwargs.pop("title", identifier),
        opened_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        **kwargs
    )


def setup_service():
    repo = InMemoryIncidentRepository()
    repo.create_incident(
        incident(
            "critical",
            severity=Severity.CRITICAL,
            owner_team=None,
            occurrence_count=3,
            most_recent_evidence=[{"token": "secret", "count": 0}],
        )
    )
    repo.create_incident(incident("low", severity=Severity.LOW, owner_team="platform"))
    repo.create_incident(incident("other-tenant", tenant="t2"))
    repo.create_incident(incident("other-env", environment="stage"))
    return IncidentWorkbenchService(repo)


def test_inbox_is_scoped_filtered_deterministic_and_cursor_bound():
    service = setup_service()
    first = service.inbox("t1", "prod", filters={"unassigned": False}, sort="severity", page_size=1, cursor=None)
    assert [item["id"] for item in first["items"]] == ["critical"]
    second = service.inbox(
        "t1", "prod", filters={"unassigned": False}, sort="severity", page_size=1, cursor=first["next_cursor"]
    )
    assert [item["id"] for item in second["items"]] == ["low"]
    with pytest.raises(CursorMismatch):
        service.inbox(
            "t1", "stage", filters={"unassigned": False}, sort="severity", page_size=1, cursor=first["next_cursor"]
        )
    assert [
        item["id"]
        for item in service.inbox(
            "t1", "prod", filters={"unassigned": True}, sort="severity", page_size=10, cursor=None
        )["items"]
    ] == ["critical"]


def test_detail_redacts_evidence_but_preserves_measured_zero():
    detail = setup_service().detail("t1", "prod", "critical", "request-1")
    assert detail["latest_evidence"] == [{"token": "[redacted]", "count": 0}]
    assert detail["missing_inputs"] == []


def test_occ_lifecycle_and_append_only_idempotent_comment():
    service = setup_service()
    detail = service.detail("t1", "prod", "critical", "r1")
    with pytest.raises(VersionConflict):
        service.mutate(
            "t1", "prod", "critical", revision="0:99", actor="u", request_id="r", state=IncidentState.ACKNOWLEDGED
        )
    changed = service.mutate(
        "t1",
        "prod",
        "critical",
        revision=detail["revision"],
        actor="u",
        request_id="r",
        state=IncidentState.ACKNOWLEDGED,
        idempotency_key="ack",
    )
    service.mutate(
        "t1",
        "prod",
        "critical",
        revision=changed["revision"],
        actor="u",
        request_id="r",
        comment="Investigating",
        idempotency_key="comment",
    )
    service.mutate(
        "t1",
        "prod",
        "critical",
        revision=changed["revision"],
        actor="u",
        request_id="r",
        comment="Investigating",
        idempotency_key="comment",
    )
    assert [event["event_type"] for event in service.timeline("t1", "prod", "critical")["items"]] == [
        "state_changed",
        "comment_added",
    ]
    with pytest.raises(ValueError, match="illegal"):
        service.mutate(
            "t1",
            "prod",
            "critical",
            revision=changed["revision"],
            actor="u",
            request_id="r",
            state=IncidentState.CLOSED,
        )


def test_action_preview_is_honest_and_deny_by_default():
    service = setup_service()
    allowed = service.preview("t1", "prod", "critical", "rerun_scan", {"api_key": "x"})
    assert allowed["provider_state"] == "not_configured" and allowed["expected_changes"] == []
    assert "api_key" not in allowed["payload_keys"]
    denied = service.preview("t1", "prod", "critical", "shell", {})
    assert denied["allowed"] is False and denied["provider_state"] == "unsupported"
