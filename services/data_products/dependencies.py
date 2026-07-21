from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[str, ...]
    truncated: bool


def build_adjacency(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    """Build stable adjacency without dropping isolated upstream nodes."""
    graph: dict[str, set[str]] = {}
    for product_id, upstream_id in edges:
        graph.setdefault(product_id, set()).add(upstream_id)
        graph.setdefault(upstream_id, set())
    return graph


def traverse(graph: dict[str, set[str]], root: str, *, max_depth: int = 8, max_nodes: int = 200) -> DependencyGraph:
    if max_depth < 0 or not 1 <= max_nodes <= 1000:
        raise ValueError("dependency bounds invalid")
    result: list[str] = []
    queue = [(root, 0)]
    seen = {root}
    truncated = False
    while queue:
        node, depth = queue.pop(0)
        if depth == max_depth and graph.get(node):
            truncated = True
            continue
        for candidate in sorted(graph.get(node, set())):
            if candidate in seen:
                continue
            if len(result) >= max_nodes:
                truncated = True
                return DependencyGraph(tuple(result), truncated)
            seen.add(candidate)
            result.append(candidate)
            queue.append((candidate, depth + 1))
    return DependencyGraph(tuple(result), truncated)


def reject_cycles(graph: dict[str, set[str]]) -> None:
    active: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            raise ValueError("data product dependency cycle")
        if node in done:
            return
        active.add(node)
        for child in sorted(graph.get(node, set())):
            visit(child)
        active.remove(node)
        done.add(node)

    for node in sorted(graph):
        visit(node)


def find_cycle_path(graph: dict[str, set[str]]) -> tuple[str, ...]:
    """Return a deterministic concrete cycle for safe 409 error responses."""
    active: list[str] = []
    done: set[str] = set()

    def visit(node: str) -> tuple[str, ...]:
        if node in active:
            offset = active.index(node)
            return tuple(active[offset:] + [node])
        if node in done:
            return ()
        active.append(node)
        for child in sorted(graph.get(node, set())):
            path = visit(child)
            if path:
                return path
        active.pop()
        done.add(node)
        return ()

    for node in sorted(graph):
        path = visit(node)
        if path:
            return path
    return ()
