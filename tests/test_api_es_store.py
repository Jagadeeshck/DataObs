"""
Unit tests for src/api/es_store.ElasticsearchStore.

All Elasticsearch client calls are mocked — no live ES cluster required.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_es_mock() -> MagicMock:
    """Return a MagicMock that satisfies ElasticsearchStore._bootstrap()."""
    es = MagicMock()
    # ILM policy already exists — don't trigger creation path
    es.ilm.get_lifecycle.return_value = {"dataobs-api-ilm": {}}
    # Indices don't exist yet — trigger creation
    es.indices.exists.return_value = False
    es.indices.create.return_value = {"acknowledged": True}
    return es


def _make_store(tenant_id: str = "test"):
    from src.api.es_store import ElasticsearchStore
    return ElasticsearchStore(_make_es_mock(), tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Bootstrap / index creation
# ---------------------------------------------------------------------------

class TestBootstrap:
    def test_creates_three_indices_on_init(self):
        es = _make_es_mock()
        from src.api.es_store import ElasticsearchStore
        ElasticsearchStore(es, tenant_id="t1")
        assert es.indices.create.call_count == 3

    def test_index_names_include_tenant(self):
        es = _make_es_mock()
        from src.api.es_store import ElasticsearchStore
        ElasticsearchStore(es, tenant_id="acme")
        created = [c.kwargs["index"] for c in es.indices.create.call_args_list]
        assert "dataobs-quality-results-acme" in created
        assert "dataobs-rules-acme" in created
        assert "dataobs-lineage-acme" in created

    def test_skips_creation_when_index_exists(self):
        es = _make_es_mock()
        es.indices.exists.return_value = True
        from src.api.es_store import ElasticsearchStore
        ElasticsearchStore(es, tenant_id="t1")
        es.indices.create.assert_not_called()

    def test_ilm_policy_created_when_missing(self):
        es = _make_es_mock()
        es.ilm.get_lifecycle.side_effect = Exception("not found")
        from src.api.es_store import ElasticsearchStore
        ElasticsearchStore(es, tenant_id="t1")
        es.ilm.put_lifecycle.assert_called_once()

    def test_ilm_policy_skipped_when_present(self):
        store = _make_store()
        store._es.ilm.put_lifecycle.assert_not_called()


# ---------------------------------------------------------------------------
# Quality results
# ---------------------------------------------------------------------------

class TestQualityResults:
    def test_save_returns_id(self):
        store = _make_store()
        store._es.index.return_value = {"_id": "abc"}
        doc_id = store.save_quality_result({"check_name": "null_check", "table": "orders", "status": "pass", "score": 1.0})
        assert isinstance(doc_id, str) and len(doc_id) > 0

    def test_save_uses_wait_for_refresh(self):
        store = _make_store()
        store._es.index.return_value = {}
        store.save_quality_result({"check_name": "x", "table": "t", "status": "pass", "score": 1.0})
        call_kwargs = store._es.index.call_args.kwargs
        assert call_kwargs.get("refresh") == "wait_for"

    def test_save_injects_tenant_id(self):
        store = _make_store(tenant_id="tenant-a")
        store._es.index.return_value = {}
        store.save_quality_result({"check_name": "x", "table": "t", "status": "pass", "score": 1.0})
        doc = store._es.index.call_args.kwargs["document"]
        assert doc["tenant_id"] == "tenant-a"

    def test_get_returns_source(self):
        store = _make_store()
        store._es.get.return_value = {"_source": {"id": "abc", "status": "pass"}}
        result = store.get_quality_result("abc")
        assert result["status"] == "pass"

    def test_get_returns_none_on_not_found(self):
        from elasticsearch import NotFoundError
        store = _make_store()
        store._es.get.side_effect = NotFoundError(404, {}, {})
        assert store.get_quality_result("missing") is None

    def test_list_applies_tenant_filter(self):
        store = _make_store(tenant_id="acme")
        store._es.search.return_value = {"hits": {"hits": []}}
        store.list_quality_results()
        query = store._es.search.call_args.kwargs["query"]
        must_terms = [c["term"] for c in query["bool"]["must"] if "term" in c]
        assert {"tenant_id": "acme"} in must_terms

    def test_list_with_table_filter(self):
        store = _make_store()
        store._es.search.return_value = {"hits": {"hits": []}}
        store.list_quality_results(table="orders")
        query = store._es.search.call_args.kwargs["query"]
        must_terms = [c["term"] for c in query["bool"]["must"] if "term" in c]
        assert {"table": "orders"} in must_terms


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class TestRules:
    def test_save_rule_returns_rule_id(self):
        store = _make_store()
        store._es.index.return_value = {}
        rule_id = store.save_rule({"dataset": "orders", "check_type": "null_check"})
        assert isinstance(rule_id, str) and len(rule_id) > 0

    def test_save_uses_wait_for_refresh(self):
        store = _make_store()
        store._es.index.return_value = {}
        store.save_rule({"dataset": "d", "check_type": "c"})
        assert store._es.index.call_args.kwargs["refresh"] == "wait_for"

    def test_add_rule_is_alias_for_save_rule(self):
        store = _make_store()
        store._es.index.return_value = {}
        r1 = store.save_rule({"dataset": "d"})
        r2 = store.add_rule({"dataset": "d"})
        assert isinstance(r1, str) and isinstance(r2, str)

    def test_get_rule_returns_none_on_missing(self):
        from elasticsearch import NotFoundError
        store = _make_store()
        store._es.get.side_effect = NotFoundError(404, {}, {})
        assert store.get_rule("missing") is None

    def test_delete_rule_returns_true(self):
        store = _make_store()
        store._es.delete.return_value = {"result": "deleted"}
        assert store.delete_rule("r1") is True

    def test_delete_rule_returns_false_on_not_found(self):
        from elasticsearch import NotFoundError
        store = _make_store()
        store._es.delete.side_effect = NotFoundError(404, {}, {})
        assert store.delete_rule("missing") is False

    def test_get_all_rules_applies_tenant_filter(self):
        store = _make_store(tenant_id="t42")
        store._es.search.return_value = {"hits": {"hits": []}}
        store.get_all_rules()
        query = store._es.search.call_args.kwargs["query"]
        assert query["term"]["tenant_id"] == "t42"

    def test_multi_tenant_isolation(self):
        """Two stores with different tenant_ids must never share index names."""
        from src.api.es_store import ElasticsearchStore
        es_a = _make_es_mock()
        es_b = _make_es_mock()
        store_a = ElasticsearchStore(es_a, tenant_id="alpha")
        store_b = ElasticsearchStore(es_b, tenant_id="beta")
        assert store_a._ri != store_b._ri
        assert store_a._qi != store_b._qi
        assert store_a._li != store_b._li


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

class TestLineage:
    def test_save_lineage_node_returns_node_id(self):
        store = _make_store()
        store._es.index.return_value = {}
        node_id = store.save_lineage_node({"type": "table", "attributes": {}})
        assert isinstance(node_id, str) and len(node_id) > 0

    def test_get_lineage_node_returns_none_on_missing(self):
        from elasticsearch import NotFoundError
        store = _make_store()
        store._es.get.side_effect = NotFoundError(404, {}, {})
        assert store.get_lineage_node("missing") is None


# ---------------------------------------------------------------------------
# Factory — get_store()
# ---------------------------------------------------------------------------

class TestGetStore:
    def test_returns_in_memory_by_default(self, monkeypatch):
        monkeypatch.delenv("DATAOBS_STORE_BACKEND", raising=False)
        from src.api.es_store import get_store
        from src.api.store import InMemoryStore
        store = get_store(es_client=None)
        assert isinstance(store, InMemoryStore)

    def test_returns_es_store_when_backend_set(self, monkeypatch):
        monkeypatch.setenv("DATAOBS_STORE_BACKEND", "elasticsearch")
        from src.api.es_store import ElasticsearchStore, get_store
        store = get_store(es_client=_make_es_mock(), tenant_id="t1")
        assert isinstance(store, ElasticsearchStore)

    def test_raises_when_es_backend_without_client(self, monkeypatch):
        monkeypatch.setenv("DATAOBS_STORE_BACKEND", "elasticsearch")
        from src.api.es_store import get_store
        with pytest.raises(ValueError, match="requires a valid es_client"):
            get_store(es_client=None)


# ---------------------------------------------------------------------------
# InMemoryStore parity checks
# ---------------------------------------------------------------------------

class TestInMemoryStore:
    """Verify InMemoryStore satisfies the same contract as ElasticsearchStore."""

    def _store(self):
        from src.api.store import InMemoryStore
        return InMemoryStore()

    def test_save_and_get_quality_result(self):
        s = self._store()
        rid = s.save_quality_result({"check_name": "null", "table": "t", "status": "pass", "score": 1.0})
        r = s.get_quality_result(rid)
        assert r["status"] == "pass"

    def test_list_quality_results_filter_table(self):
        s = self._store()
        s.save_quality_result({"table": "orders", "status": "pass", "score": 1.0, "check_name": "c"})
        s.save_quality_result({"table": "users",  "status": "fail", "score": 0.0, "check_name": "c"})
        results = s.list_quality_results(table="orders")
        assert len(results) == 1 and results[0]["table"] == "orders"

    def test_save_and_delete_rule(self):
        s = self._store()
        rid = s.save_rule({"dataset": "d", "check_type": "null"})
        assert s.delete_rule(rid) is True
        assert s.get_rule(rid) is None

    def test_delete_missing_rule_returns_false(self):
        s = self._store()
        assert s.delete_rule("nonexistent") is False

    def test_get_all_rules_sorted_by_dataset(self):
        s = self._store()
        s.save_rule({"rule_id": "r1", "dataset": "zebra"})
        s.save_rule({"rule_id": "r2", "dataset": "alpha"})
        rules = s.get_all_rules()
        assert rules[0]["dataset"] == "alpha"

    def test_multi_instance_isolation(self):
        """Two InMemoryStore instances must not share state."""
        from src.api.store import InMemoryStore
        a, b = InMemoryStore(), InMemoryStore()
        a.save_rule({"rule_id": "r1", "dataset": "d"})
        assert b.get_all_rules() == []
