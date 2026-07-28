"""Regression coverage for Elasticsearch reconciliation precision contracts."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from services.data_products.elasticsearch_repository import (
    DEPENDENCIES,
    ElasticsearchDataProductRepository,
)
from services.data_products.elasticsearch_repository_base import (
    ElasticsearchDataProductRepository as BaseElasticsearchDataProductRepository,
)
from services.data_products.operation_state import DataProductOperationState


class FakeClient:
    def __init__(self, hits=()):
        self.hits = list(hits)
        self.calls = []
        self.indices = SimpleNamespace(refresh=Mock())

    def search(self, **request):
        self.calls.append(request)
        return {"hits": {"hits": self.hits}}


def _hit(repository, operation_id, instant, *, due=None, status="pending", expiry=None):
    state = DataProductOperationState(
        operation_id,
        "tenant",
        "production",
        "product",
        "manual_membership",
        status,
        0,
        instant,
        claim_owner="worker" if status == "claimed" else None,
        claim_generation=1 if status == "claimed" else 0,
        claimed_at=instant if status == "claimed" else None,
        claim_expires_at=expiry,
        next_attempt_at=due,
        plan_reference=f"plan:{operation_id}",
    )
    return {
        "_source": repository._state_document(state),
        "_seq_no": 1,
        "_primary_term": 1,
        "sort": [due.isoformat() if due else None, operation_id],
    }


def test_reconcilable_selection_applies_exact_microsecond_boundaries():
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bootstrap = ElasticsearchDataProductRepository(FakeClient())
    hits = [
        _hit(bootstrap, "missing", instant),
        _hit(bootstrap, "past", instant, due=instant - timedelta(microseconds=1)),
        _hit(bootstrap, "exact", instant, due=instant),
        _hit(bootstrap, "future", instant, due=instant + timedelta(microseconds=1)),
        _hit(
            bootstrap,
            "claimed-future",
            instant,
            status="claimed",
            expiry=instant + timedelta(microseconds=1),
        ),
    ]
    client = FakeClient(hits)
    repository = ElasticsearchDataProductRepository(client)

    selected = repository.list_reconcilable_operations("tenant", "production", now=instant, limit=3)

    assert [state.operation_id for state in selected] == ["missing", "past", "exact"]
    assert client.calls[0]["sort"] == [
        {"next_attempt_at": {"order": "asc", "missing": "_first"}},
        {"operation_id": "asc"},
    ]


def test_operation_history_uses_mapped_event_identifier_for_tie_breaking():
    client = FakeClient()
    repository = ElasticsearchDataProductRepository(client)

    assert repository.get_operation_history("tenant", "production", "operation") == []
    assert client.calls[0]["sort"] == [
        {"occurred_at": "asc"},
        {"document.event_id": "asc"},
    ]


def test_dependency_chunk_refreshes_once_after_writes(monkeypatch):
    def no_op_chunk(self, tenant_id, environment, product_id, edges, *, tombstone):
        return None

    monkeypatch.setattr(
        BaseElasticsearchDataProductRepository,
        "_apply_dependency_chunk",
        no_op_chunk,
    )
    client = FakeClient()
    repository = ElasticsearchDataProductRepository(client)

    repository._apply_dependency_chunk("tenant", "production", "product", (object(),), tombstone=False)

    client.indices.refresh.assert_called_once_with(index=DEPENDENCIES)
