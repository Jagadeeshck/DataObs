from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from packages.domain_model.incident import Incident, Severity
from packages.elastic_store.registry import _mapping
from services.incident_manager.repository import InMemoryIncidentRepository
from services.incident_manager.timeline_storage import timeline_document_to_event, timeline_event_to_document
from services.incident_manager.workbench import CursorMismatch, IncidentWorkbenchService
from src.api.incident_routes import authenticated_actor


def _incident(number: int, *, severity: Severity = Severity.LOW) -> Incident:
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=number)
    return Incident(
        id=f"i-{number:03}",
        tenant_id="tenant",
        environment="prod",
        deduplication_key=str(number),
        title=f"incident {number}",
        severity=severity,
        occurrence_count=number,
        opened_at=observed,
        last_observed_at=observed,
    )


def test_timeline_adapter_matches_generated_strict_mapping_and_round_trips():
    event = {
        "tenant_id": "tenant",
        "environment": "prod",
        "incident_id": "i-1",
        "event_id": "event-1",
        "event_type": "comment_added",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "actor": "alice",
        "summary": "token=secret-value",
        "revision": 7,
        "request_id": "request-1",
    }
    document = timeline_event_to_document(event)
    assert set(document) <= set(_mapping()["properties"])
    assert "@timestamp" in document and "timestamp" not in document
    assert "event_id" not in document and "actor" not in document
    assert isinstance(document["revision"], int)
    assert "secret-value" not in document["summary"]
    decoded = timeline_document_to_event(document)
    assert (decoded["event_id"], decoded["actor"], decoded["event_type"]) == ("event-1", "alice", "comment_added")


def test_keyset_query_finds_and_sorts_more_than_former_200_boundary():
    repository = InMemoryIncidentRepository()
    for number in range(250):
        repository.create_incident(_incident(number, severity=Severity.CRITICAL if number == 249 else Severity.LOW))
    service = IncidentWorkbenchService(repository)
    cursor = None
    identifiers = []
    while True:
        page = service.inbox("tenant", "prod", filters={}, sort="severity", page_size=37, cursor=cursor)
        identifiers.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(identifiers) == len(set(identifiers)) == 250
    assert identifiers[0] == "i-249"


def test_cursor_is_signed_and_bound_to_query():
    repository = InMemoryIncidentRepository()
    repository.create_incident(_incident(1))
    repository.create_incident(_incident(2))
    service = IncidentWorkbenchService(repository)
    cursor = service.inbox("tenant", "prod", filters={}, sort="newest_opened", page_size=1, cursor=None)["next_cursor"]
    assert cursor
    with pytest.raises(CursorMismatch):
        service.inbox("tenant", "prod", filters={}, sort="occurrence_count", page_size=1, cursor=cursor)
    position = len(cursor) // 2
    tampered = cursor[:position] + ("A" if cursor[position] != "A" else "B") + cursor[position + 1 :]
    with pytest.raises(CursorMismatch):
        service.inbox("tenant", "prod", filters={}, sort="newest_opened", page_size=1, cursor=tampered)


def test_retry_reconciles_timeline_failure_without_reapplying_mutation():
    class FailOnceRepository(InMemoryIncidentRepository):
        failures = 1

        def append_event(self, event):
            if self.failures:
                self.failures -= 1
                raise RuntimeError("simulated timeline outage")
            super().append_event(event)

    repository = FailOnceRepository()
    repository.create_incident(_incident(1))
    service = IncidentWorkbenchService(repository)
    revision = service.detail("tenant", "prod", "i-001", "request")["revision"]
    with pytest.raises(RuntimeError, match="timeline outage"):
        service.mutate(
            "tenant",
            "prod",
            "i-001",
            revision=revision,
            actor="alice",
            request_id="request",
            owner="platform",
            idempotency_key="assign-platform",
        )
    recovered = service.mutate(
        "tenant",
        "prod",
        "i-001",
        revision=revision,
        actor="alice",
        request_id="request",
        owner="platform",
        idempotency_key="assign-platform",
    )
    assert recovered["owner"] == "platform"
    assert len(repository.events) == 1
    assert repository.get_incident("tenant", "i-001", "prod").seq_no == 1


def test_actor_uses_validated_principal_and_fails_closed():
    request = SimpleNamespace(
        state=SimpleNamespace(principal=SimpleNamespace(subject="alice"), subject="wrong-attribute")
    )
    assert authenticated_actor(request) == "alice"
    with pytest.raises(HTTPException) as error:
        authenticated_actor(SimpleNamespace(state=SimpleNamespace()))
    assert error.value.status_code == 401
