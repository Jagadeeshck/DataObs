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
    page_count: int = 0
    elapsed_ms: int = 0
    truncated: bool = False
    truncation_reason: str | None = None


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[str, ...]
    truncated: bool
    edges: tuple[tuple[str, str], ...] = ()
    stats: DataProductDependencyTraversalStats | None = None
    cycle_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrontierPageRequest:
    frontier: tuple[str, ...]
    direction: Literal["upstream", "downstream"]
    search_after: tuple[str | int | float, ...] | None = None


@dataclass(frozen=True)
class FrontierPageResult:
    edges: tuple[tuple[str, str], ...]
    search_after: tuple[str | int | float, ...] | None = None


class TraversalBudgetTracker:
    """Charges each physical backend page; loaders cannot hide free searches."""

    def __init__(self, budget: DataProductDependencyTraversalBudget) -> None:
        self.budget = budget
        self.started = monotonic()
        self.query_count = self.page_count = self.edge_count = 0

    @property
    def elapsed_ms(self) -> int:
        return int((monotonic() - self.started) * 1000)

    def before_request(self) -> None:
        if self.query_count >= self.budget.max_queries:
            raise TraversalBudgetExhausted("max_queries")
        if self.elapsed_ms >= self.budget.timeout_ms:
            raise TraversalBudgetExhausted("timeout_ms")
        self.query_count += 1

    def after_response(self, edge_count: int) -> None:
        self.page_count += 1
        self.edge_count += edge_count
        if self.edge_count > self.budget.max_edges:
            raise TraversalBudgetExhausted("max_edges")


class TraversalBudgetExhausted(RuntimeError):
    pass


@dataclass(frozen=True)
class DependencyCycleValidationResult:
    cycle_detected: bool
    cycle_path: tuple[str, ...]
    visited_count: int
    edge_count: int
    query_count: int
    truncated: bool
    truncation_reason: str | None = None


def validate_dependency_replacement_cycle(
    product_id: str,
    proposed_upstream_ids: Sequence[str],
    budget: DataProductDependencyTraversalBudget,
    loader: FrontierLoader,
) -> DependencyCycleValidationResult:
    """Fail-closed relevant-graph validation after logical outgoing replacement."""
    combined_edges: set[tuple[str, str]] = {(product_id, upstream) for upstream in proposed_upstream_ids}
    visited: set[str] = {product_id}
    query_count = 0
    for upstream in sorted(set(proposed_upstream_ids)):
        result = traverse_frontiers(upstream, "upstream", budget, loader)
        combined_edges.update(result.edges)
        visited.update(result.nodes)
        query_count += result.stats.query_count if result.stats else 0
        if result.truncated:
            return DependencyCycleValidationResult(
                False,
                (),
                len(visited),
                len(combined_edges),
                query_count,
                True,
                result.stats.truncation_reason if result.stats else "incomplete",
            )
    path = find_cycle_path(build_adjacency(combined_edges))
    relevant = path if path and product_id in path else ()
    return DependencyCycleValidationResult(
        bool(relevant), relevant, len(visited), len(combined_edges), query_count, False
    )


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
    elapsed_ms = int((monotonic() - started) * 1000)
    stats = DataProductDependencyTraversalStats(
        depth, len(seen), len(selected), queries, queries, elapsed_ms, reason is not None, reason
    )
    return DependencyGraph(tuple(nodes), stats.truncated, tuple(sorted(selected)), stats, cycle)
