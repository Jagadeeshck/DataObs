"""Opt-in strict-mapping certification; requires a disposable Elasticsearch 9.5.5 node."""

import os

import pytest
from elasticsearch import Elasticsearch

from packages.elastic_store.registry import apply, status
from services.incident_manager.elasticsearch_repository import ElasticsearchIncidentRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="requires isolated Elasticsearch 9.5.5"
)


def _delete_dataobs_indices(client: Elasticsearch) -> None:
    indices = client.indices.get(
        index="dataobs-*",
        allow_no_indices=True,
        ignore_unavailable=True,
        expand_wildcards="all",
    )
    for index_name in sorted(indices):
        client.indices.delete(index=index_name)


@pytest.fixture()
def repository():
    client = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
    _delete_dataobs_indices(client)
    apply(client)
    assert status(client)["ready"] is True
    yield ElasticsearchIncidentRepository(client)
    _delete_dataobs_indices(client)


def _event(identifier="event-1", tenant="tenant", environment="prod"):
    return {
        "tenant_id": tenant,
        "environment": environment,
        "incident_id": "incident-1",
        "event_id": identifier,
        "event_type": "comment_added",
        "timestamp": "2026-01-01T00:00:00Z",
        "actor": "alice",
        "summary": "safe",
        "revision": 1,
        "request_id": "request-1",
    }


def test_strict_timeline_mapping_idempotency_scope_decode_and_pagination(repository):
    repository.append_event(_event())
    repository.append_event(_event())
    repository.append_event(_event("event-other-tenant", tenant="other"))
    repository.append_event(_event("event-other-environment", environment="stage"))
    repository.append_event(_event("event-2"))
    first = repository.search_events("tenant", "prod", "incident-1", 1, None)
    second = repository.search_events("tenant", "prod", "incident-1", 1, first.sort_values)
    assert [first.items[0]["event_id"], second.items[0]["event_id"]] == ["event-1", "event-2"]
    assert first.items[0]["actor"] == "alice"
