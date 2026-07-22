from services.data_products.dependencies import (
    DataProductDependencyTraversalBudget,
    build_adjacency,
    find_cycle_path,
    traverse_frontiers,
)
from services.data_products.dependency_events import (
    canonical_upstream_ids,
    dependency_request_fingerprint,
)


def test_canonical_fingerprint_ignores_order_and_duplicates():
    kwargs = dict(tenant_id="t", environment="prod", product_id="p", actor="a", reason="r", expected_product_etag="e")
    assert canonical_upstream_ids("p", ["b", "a", "b"]) == ("a", "b")
    assert dependency_request_fingerprint(upstream_product_ids=["b", "a"], **kwargs) == dependency_request_fingerprint(
        upstream_product_ids=["a", "b", "a"], **kwargs
    )


def test_full_deterministic_cycle_path():
    graph = build_adjacency([("a", "b"), ("b", "c"), ("c", "a")])
    assert find_cycle_path(graph) == ("a", "b", "c", "a")


def test_frontier_paginates_large_graph_without_tenant_wide_read():
    edges = [("root", f"p-{number:04}") for number in range(1200)]
    calls = []

    def loader(frontier, direction):
        calls.append(tuple(frontier))
        return [edge for edge in edges if edge[0] in frontier], True

    result = traverse_frontiers(
        "root",
        "upstream",
        DataProductDependencyTraversalBudget(max_depth=2, max_nodes=1300, max_edges=1300, max_terms_per_query=50),
        loader,
    )
    assert len(result.nodes) == 1200
    assert not result.truncated
    assert calls[0] == ("root",)


def test_frontier_reports_budget_truncation():
    result = traverse_frontiers(
        "root",
        "upstream",
        DataProductDependencyTraversalBudget(max_nodes=2),
        lambda frontier, direction: ([("root", "a"), ("root", "b")], True),
    )
    assert result.truncated
    assert result.stats and result.stats.truncation_reason == "max_nodes"
