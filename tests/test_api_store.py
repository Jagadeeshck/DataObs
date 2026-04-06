from src.api.store import LineageStore, RuleStore


def test_rule_store_upsert_list_delete():
    store = RuleStore()
    store.upsert_rule("rule-1", {"dataset": "prod.orders", "check": "freshness"})

    listed = store.list_rules()
    assert len(listed) == 1
    assert listed[0]["rule_id"] == "rule-1"

    assert store.delete_rule("rule-1") is True
    assert store.list_rules() == []


def test_lineage_store_downstream_traversal():
    store = LineageStore()
    store.add_edge({"source_node_id": "raw.orders", "target_node_id": "stg.orders"})
    store.add_edge({"source_node_id": "stg.orders", "target_node_id": "mart.orders"})

    downstream = store.downstream("raw.orders", depth=5)

    assert downstream == ["stg.orders", "mart.orders"]
