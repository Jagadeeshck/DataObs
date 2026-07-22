"""Deterministic, budgeted dependency graph algorithms.

Repository implementations are responsible for fetching each frontier; keeping the
algorithm here makes budget and completeness semantics identical in memory and ES.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable, Iterable, Literal, Sequence


@dataclass(frozen=True)
class DataProductDependencyTraversalBudget:
    max_depth: int = 8
    max_nodes: int = 200
    max_edges: int = 1000
    max_queries: int = 100
    max_terms_per_query: int = 100
    timeout_ms: int = 5000
    page_size: int = 200

    def __post_init__(self) -> None:
        values = (
            self.max_depth,
            self.max_nodes,
            self.max_edges,
            self.max_queries,
            self.max_terms_per_query,
            self.timeout_ms,
            self.page_size,
        )
        if any(value < 1 for value in values):
            raise ValueError("dependency traversal budgets must be positive")


@dataclass(frozen=True)
class DataProductDependencyTraversalStats:
    depth_reached: int
    visited_count: int
    edge_count: int
    query_count: int
    truncated: bool = False
    truncation_reason: str | None = None


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[str, ...]
    truncated: bool
    edges: tuple[tuple[str, str], ...] = ()
    stats: DataProductDependencyTraversalStats | None = None
    cycle_path: tuple[str, ...] = ()


def build_adjacency(edges: Iterable[tuple[str, str]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for product_id, upstream_id in edges:
        graph.setdefault(product_id, set()).add(upstream_id)
        graph.setdefault(upstream_id, set())
    return graph


def find_cycle_path(graph: dict[str, set[str]]) -> tuple[str, ...]:
    """Return the lexicographically deterministic, complete first cycle."""
    active: list[str] = []
    active_set: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> tuple[str, ...]:
        if node in active_set:
            offset = active.index(node)
            return tuple(active[offset:] + [node])
        if node in done:
            return ()
        active.append(node)
        active_set.add(node)
        for child in sorted(graph.get(node, ())):
            path = visit(child)
            if path:
                return path
        active.pop()
        active_set.remove(node)
        done.add(node)
        return ()

    for node in sorted(graph):
        path = visit(node)
        if path:
            return path
    return ()


def reject_cycles(graph: dict[str, set[str]]) -> None:
    path = find_cycle_path(graph)
    if path:
        raise ValueError("data product dependency cycle")


def traverse(graph: dict[str, set[str]], root: str, *, max_depth: int = 8, max_nodes: int = 200) -> DependencyGraph:
    budget = DataProductDependencyTraversalBudget(max_depth=max_depth, max_nodes=max_nodes)
    return traverse_frontiers(
        root,
        "upstream",
        budget,
        lambda frontier, _: ([(node, child) for node in frontier for child in sorted(graph.get(node, ()))], True),
    )


FrontierLoader = Callable[[Sequence[str], Literal["upstream", "downstream"]], tuple[Sequence[tuple[str, str]], bool]]


def traverse_frontiers(
    root: str,
    direction: Literal["upstream", "downstream"],
    budget: DataProductDependencyTraversalBudget,
    loader: FrontierLoader,
) -> DependencyGraph:
    """Breadth-first traversal whose loader reports whether every page was read."""
    started = monotonic()
    frontier = [root]
    seen = {root}
    nodes: list[str] = []
    selected: set[tuple[str, str]] = set()
    parents: dict[str, str] = {}
    cycle: tuple[str, ...] = ()
    queries = depth = 0
    reason: str | None = None

    while frontier and depth < budget.max_depth:
        next_frontier: set[str] = set()
        for offset in range(0, len(frontier), budget.max_terms_per_query):
            if queries >= budget.max_queries:
                reason = "max_queries"
                break
            if (monotonic() - started) * 1000 >= budget.timeout_ms:
                reason = "timeout_ms"
                break
            chunk = frontier[offset : offset + budget.max_terms_per_query]
            edges, complete = loader(chunk, direction)
            queries += 1
            if not complete:
                reason = "incomplete_page"
                break
            for product, upstream in sorted(set(edges)):
                source, target = (product, upstream) if direction == "upstream" else (upstream, product)
                if source not in chunk:
                    continue
                if len(selected) >= budget.max_edges:
                    reason = "max_edges"
                    break
                selected.add((product, upstream))
                if target in seen:
                    # Reconstruct a useful closed path when this is an ancestor.
                    chain = [source]
                    while chain[-1] in parents and len(chain) <= len(seen):
                        chain.append(parents[chain[-1]])
                        if chain[-1] == target:
                            cycle = tuple(reversed(chain)) + (target,)
                            break
                    continue
                if len(seen) >= budget.max_nodes:
                    reason = "max_nodes"
                    break
                seen.add(target)
                parents[target] = source
                nodes.append(target)
                next_frontier.add(target)
            if reason:
                break
        depth += 1
        if reason:
            break
        frontier = sorted(next_frontier)
    if frontier and depth >= budget.max_depth:
        reason = "max_depth"
    stats = DataProductDependencyTraversalStats(depth, len(seen), len(selected), queries, reason is not None, reason)
    return DependencyGraph(tuple(nodes), stats.truncated, tuple(sorted(selected)), stats, cycle)
