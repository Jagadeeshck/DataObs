from services.data_products.dependencies import build_adjacency, reject_cycles, traverse


def test_dependency_traversal_is_stable_and_bounded():
    graph = build_adjacency([("p", "b"), ("p", "a"), ("a", "c")])
    assert traverse(graph, "p").nodes == ("a", "b", "c")
    assert traverse(graph, "p", max_nodes=1).truncated is True


def test_dependency_cycle_is_rejected_independent_of_input_order():
    graph = build_adjacency([("b", "a"), ("a", "b")])
    try:
        reject_cycles(graph)
    except ValueError as exc:
        assert str(exc) == "data product dependency cycle"
    else:
        raise AssertionError("cycle accepted")
