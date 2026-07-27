"""Store-layer tests for in-memory and legacy compatibility adapters."""

from __future__ import annotations

from src.api.store import InMemoryStore, LineageStore, RuleStore


class _FakeES:
    """Simulates a minimal Elasticsearch client for legacy adapter tests."""

    def __init__(self):
        self._docs: dict = {}

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
        if query and "term" in query:
            field, value = next(iter(query["term"].items()))
            bare_field = field.replace(".keyword", "")
            hits = [h for h in hits if h["_source"].get(bare_field) == value]
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
        return None


def test_memory_store_rule_crud_roundtrip():
    store = InMemoryStore()
    rule_id = store.add_rule({"dataset": "prod.orders", "check_type": "freshness"})
    assert store.get_rule(rule_id)["dataset"] == "prod.orders"
    assert store.get_rules_for_dataset("prod.orders")[0]["rule_id"] == rule_id
    assert store.delete_rule(rule_id) is True
    assert store.get_rule(rule_id) is None


def test_memory_store_quality_save_list_and_filters():
    store = InMemoryStore()
    store.save_quality_result({"id": "q1", "check_name": "null", "table": "orders", "status": "pass", "score": 1.0})
    store.save_quality_result(
        {"id": "q2", "check_name": "freshness", "table": "orders", "status": "fail", "score": 0.2}
    )
    store.save_quality_result({"id": "q3", "check_name": "null", "table": "users", "status": "pass", "score": 0.9})

    assert len(store.list_quality_results()) == 3
    assert {r["id"] for r in store.list_quality_results(table="orders")} == {"q1", "q2"}
    assert {r["id"] for r in store.list_quality_results(status="pass")} == {"q1", "q3"}


def test_memory_store_lineage_bfs_traversal():
    store = InMemoryStore()
    for node_id in ["raw.orders", "stg.orders", "mart.orders", "app.reports"]:
        store.save_lineage_node({"node_id": node_id, "type": "table"})
    store.save_lineage_edge({"source_node_id": "raw.orders", "target_node_id": "stg.orders"})
    store.save_lineage_edge({"source_node_id": "stg.orders", "target_node_id": "mart.orders"})
    store.save_lineage_edge({"source_node_id": "mart.orders", "target_node_id": "app.reports"})

    assert len(store.get_all_nodes()) == 4
    assert len(store.get_all_edges()) == 3
    assert store.get_downstream_impact("raw.orders", depth=2) == ["stg.orders", "mart.orders"]
    assert store.get_downstream_impact("raw.orders", depth=5) == ["stg.orders", "mart.orders", "app.reports"]


# Legacy adapter checks (kept for migration compatibility)


def test_legacy_rule_store_add_and_list():
    store = RuleStore(_FakeES())
    rule_id = store.add_rule({"dataset": "prod.orders", "check_type": "freshness", "severity": "critical"})
    assert rule_id is not None
    assert len(store.get_all_rules()) == 1


def test_legacy_lineage_store_downstream_impact():
    es = _FakeES()
    es._docs["dataobs-lineage-edges"] = {
        "e1": {"source_node_id": "raw.orders", "target_node_id": "stg.orders"},
        "e2": {"source_node_id": "stg.orders", "target_node_id": "mart.orders"},
    }

    store = LineageStore(es)
    affected = store.get_downstream_impact("raw.orders", depth=5)
    assert "stg.orders" in affected
    assert "mart.orders" in affected
