"""Unit tests for the asset catalog search repository (0035 projection).

Fake in-memory ES — no live cluster. Validates tenant/environment scoping,
BM25 field boosting in the query, facet aggregation passthrough, and honest
states: measured zero vs unavailable (missing index) vs error.
"""

from __future__ import annotations

from services.product_query.asset_search_repository import (
    ASSET_SEARCH_INDEX,
    AssetSearchRepository,
)


class _MissingIndexError(Exception):
    status_code = 404


class _RecordingES:
    def __init__(self, response=None, raise_exc=None):
        self._response = response or {"hits": {"total": {"value": 0}, "hits": []}, "aggregations": {}}
        self._raise = raise_exc
        self.last_call = None

    def search(self, **kwargs):
        self.last_call = kwargs
        if self._raise is not None:
            raise self._raise
        return self._response


def test_query_is_tenant_and_environment_scoped_with_boosted_fields():
    es = _RecordingES()
    repo = AssetSearchRepository(es)
    repo.search("acme", "production", text="orders", limit=10)

    assert es.last_call["index"] == ASSET_SEARCH_INDEX
    filters = es.last_call["query"]["bool"]["filter"]
    assert {"term": {"tenant_id": "acme"}} in filters
    assert {"term": {"environment": "production"}} in filters
    # BM25 multi_match with field boosts on display_name/search_text.
    must = es.last_call["query"]["bool"]["must"]
    mm = must[0]["multi_match"]
    assert mm["query"] == "orders"
    assert "display_name^3" in mm["fields"]
    assert "search_text^2" in mm["fields"]
    # Raw search_text is never returned to the caller.
    assert "search_text" in es.last_call["source_excludes"]


def test_facet_filter_adds_exact_term():
    es = _RecordingES()
    repo = AssetSearchRepository(es)
    repo.search("acme", "production", filters={"asset_type": "table", "owner_team": "data-eng"})
    filters = es.last_call["query"]["bool"]["filter"]
    assert {"term": {"asset_type": "table"}} in filters
    assert {"term": {"owner_team": "data-eng"}} in filters


def test_no_text_uses_match_all():
    es = _RecordingES()
    repo = AssetSearchRepository(es)
    repo.search("acme", "production")
    assert es.last_call["query"]["bool"]["must"][0] == {"match_all": {}}


def test_measured_zero_is_complete_not_unavailable():
    es = _RecordingES(response={"hits": {"total": {"value": 0}, "hits": []}, "aggregations": {}})
    result = AssetSearchRepository(es).search("acme", "production", text="nothing")
    assert result.data_status == "complete"
    assert result.total == 0
    assert result.items == []


def test_results_and_facets_passthrough():
    response = {
        "hits": {
            "total": {"value": 2},
            "hits": [
                {"_source": {"asset_id": "a1", "display_name": "orders"}},
                {"_source": {"asset_id": "a2", "display_name": "order_items"}},
            ],
        },
        "aggregations": {
            "asset_type": {"buckets": [{"key": "table", "doc_count": 2}]},
            "owner_team": {"buckets": []},
            "classification": {"buckets": []},
            "business_service": {"buckets": []},
        },
    }
    result = AssetSearchRepository(_RecordingES(response=response)).search("acme", "production", text="order")
    assert result.data_status == "complete"
    assert result.total == 2
    assert [i["asset_id"] for i in result.items] == ["a1", "a2"]
    assert result.facets["asset_type"] == [{"value": "table", "count": 2}]


def test_missing_index_is_unavailable_not_error():
    es = _RecordingES(raise_exc=_MissingIndexError("index_not_found_exception"))
    result = AssetSearchRepository(es).search("acme", "production", text="x")
    assert result.data_status == "unavailable"
    assert result.total == 0
    assert result.items == []


def test_transport_error_is_error_never_silent_zero():
    es = _RecordingES(raise_exc=RuntimeError("connection reset"))
    result = AssetSearchRepository(es).search("acme", "production", text="x")
    assert result.data_status == "error"
    assert result.items == []


def test_limit_is_bounded():
    es = _RecordingES()
    AssetSearchRepository(es).search("acme", "production", limit=9999)
    assert es.last_call["size"] == 100  # clamped to _MAX_SIZE
