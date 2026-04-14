"""
Tests for the ES-backed RuleStore and LineageStore.

Uses a minimal fake Elasticsearch client — no real ES needed.
"""
from __future__ import annotations

from src.api.store import LineageStore, RuleStore


# ---------------------------------------------------------------------------
# Fake Elasticsearch client
# ---------------------------------------------------------------------------

class _FakeES:
    """Simulates a minimal Elasticsearch client for store tests."""

    def __init__(self):
        self._docs: dict = {}   # index -> {id: doc}
        self._edges: list[dict] = []

    @property
    def indices(self):
        return _FakeIndices()

    def index(self, index: str, document: dict = None, id: str = None, **kwargs) -> dict:
        doc = document or kwargs.get("document", {})
        self._docs.setdefault(index, {})[id or "auto"] = doc
        return {"result": "created"}

    def search(self, index: str, query: dict = None, size: int = 1000, **kwargs) -> dict:
        docs = self._docs.get(index, {})
        hits = [{"_source": v, "_id": k} for k, v in docs.items()]
        # Simple term filter support
        if query and "term" in query:
            field, value = next(iter(query["term"].items()))
            hits = [h for h in hits if h["_source"].get(field) == value]
        return {"hits": {"hits": hits[:size]}}

    def delete(self, index: str, id: str) -> dict:
        from elasticsearch import NotFoundError
        bucket = self._docs.get(index, {})
        if id not in bucket:
            raise NotFoundError(404, "Not found", {})
        del bucket[id]
        return {"result": "deleted"}


class _FakeIndices:
    def exists(self, index: str) -> bool:
        return True

    def create(self, index: str, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# RuleStore tests
# ---------------------------------------------------------------------------

def test_rule_store_add_and_list():
    store = RuleStore(_FakeES())
    rule_id = store.add_rule({
        "dataset": "prod.orders",
        "check_type": "freshness",
        "severity": "critical",
    })
    assert rule_id is not None

    rules = store.get_all_rules()
    assert len(rules) == 1
    assert rules[0]["dataset"] == "prod.orders"


def test_rule_store_delete_existing_rule():
    es = _FakeES()
    store = RuleStore(es)
    rule_id = store.add_rule({"rule_id": "rule-1", "dataset": "prod.orders"})

    deleted = store.delete_rule(rule_id)
    assert deleted is True


def test_rule_store_delete_nonexistent_rule_returns_false():
    store = RuleStore(_FakeES())
    assert store.delete_rule("does-not-exist") is False


def test_rule_store_get_rules_for_dataset():
    store = RuleStore(_FakeES())
    store.add_rule({"dataset": "prod.orders", "check_type": "null_check"})
    store.add_rule({"dataset": "prod.customers", "check_type": "freshness"})

    # Dataset filter relies on term query; fake ES supports it
    results = store.get_rules_for_dataset("prod.orders")
    datasets = [r["dataset"] for r in results]
    assert all(d == "prod.orders" for d in datasets)


# ---------------------------------------------------------------------------
# LineageStore tests
# ---------------------------------------------------------------------------

def test_lineage_store_get_all_nodes():
    es = _FakeES()
    # Pre-seed a node document
    es._docs["dataobs-lineage-nodes"] = {
        "rds.prod.orders": {"node_id": "rds.prod.orders", "node_type": "table"}
    }
    store = LineageStore(es)
    nodes = store.get_all_nodes()
    assert len(nodes) == 1
    assert nodes[0]["node_id"] == "rds.prod.orders"


def test_lineage_store_get_all_edges():
    es = _FakeES()
    es._docs["dataobs-lineage-edges"] = {
        "e1": {"source_node_id": "raw.orders", "target_node_id": "stg.orders"}
    }
    store = LineageStore(es)
    edges = store.get_all_edges()
    assert len(edges) == 1


def test_lineage_store_downstream_impact():
    """BFS traversal via get_downstream_impact uses source_node_id term query."""
    es = _FakeES()
    # Graph: raw.orders -> stg.orders -> mart.orders
    es._docs["dataobs-lineage-edges"] = {
        "e1": {"source_node_id": "raw.orders", "target_node_id": "stg.orders"},
        "e2": {"source_node_id": "stg.orders", "target_node_id": "mart.orders"},
    }

    # Patch search to filter on source_node_id (not keyword field)
    original_search = es.search

    def patched_search(index, query=None, size=100, **kwargs):
        docs = es._docs.get(index, {})
        hits = [{"_source": v} for v in docs.values()]
        if query and "term" in query:
            field, value = next(iter(query["term"].items()))
            # Strip .keyword suffix for fake comparison
            bare_field = field.replace(".keyword", "")
            hits = [h for h in hits if h["_source"].get(bare_field) == value]
        return {"hits": {"hits": hits[:size]}}

    es.search = patched_search

    store = LineageStore(es)
    affected = store.get_downstream_impact("raw.orders", depth=5)
    assert "stg.orders" in affected
    assert "mart.orders" in affected
