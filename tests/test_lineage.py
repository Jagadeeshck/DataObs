"""
Unit tests for LineageTracker BFS traversal logic.

Uses a fake Elasticsearch client that simulates a small in-memory graph
so no real ES instance is required.
"""
from __future__ import annotations

from src.quality.lineage import LineageEdge, LineageNode, LineageTracker, NodeType


# ---------------------------------------------------------------------------
# Fake Elasticsearch client
# ---------------------------------------------------------------------------

class _FakeES:
    """
    Simulates an Elasticsearch client for lineage tests.

    Graph is stored as a list of (source, target) pairs.  search() filters
    edges by source_node_id or target_node_id depending on the query term.
    """

    def __init__(self, edges: list[tuple[str, str]]):
        # edges: list of (source_node_id, target_node_id)
        self._edges = edges
        self._nodes: dict[str, dict] = {}
        self.indexed_docs: list[dict] = []

    # ── ES indices stub ───────────────────────────────────────────────────

    @property
    def indices(self):
        return _FakeIndices()

    # ── Core methods ──────────────────────────────────────────────────────

    def search(self, index: str, query: dict, size: int = 100, **kwargs) -> dict:
        term = query.get("term", {})
        hits = []

        if "source_node_id.keyword" in term:
            src = term["source_node_id.keyword"]
            for s, t in self._edges:
                if s == src:
                    hits.append({"_source": {"target_node_id": t}})

        elif "target_node_id.keyword" in term:
            tgt = term["target_node_id.keyword"]
            for s, t in self._edges:
                if t == tgt:
                    hits.append({"_source": {"source_node_id": s}})

        return {"hits": {"hits": hits[:size]}}

    def update(self, index: str, id: str, **kwargs) -> None:
        self._nodes[id] = kwargs.get("doc", {})

    def index(self, index: str, document: dict, **kwargs) -> None:
        self.indexed_docs.append({"index": index, "doc": document})


class _FakeIndices:
    def exists(self, index: str) -> bool:
        return True  # pretend indices already exist — skip _ensure_indices

    def create(self, index: str, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tracker(edges: list[tuple[str, str]]) -> LineageTracker:
    es = _FakeES(edges)
    return LineageTracker(es)


# ---------------------------------------------------------------------------
# Tests: get_downstream_impact (BFS downstream)
# ---------------------------------------------------------------------------

def test_downstream_impact_direct_children():
    """A -> B and A -> C: impact of A should be [B, C]."""
    tracker = _make_tracker([("A", "B"), ("A", "C")])
    result = tracker.get_downstream_impact("A", depth=1)
    assert set(result) == {"B", "C"}


def test_downstream_impact_multi_hop():
    """A -> B -> C: impact of A at depth 2 should include both B and C."""
    tracker = _make_tracker([("A", "B"), ("B", "C")])
    result = tracker.get_downstream_impact("A", depth=2)
    assert "B" in result
    assert "C" in result


def test_downstream_impact_depth_limit():
    """A -> B -> C -> D: with depth=1, only B should appear."""
    tracker = _make_tracker([("A", "B"), ("B", "C"), ("C", "D")])
    result = tracker.get_downstream_impact("A", depth=1)
    assert result == ["B"]


def test_downstream_impact_no_downstream():
    """Leaf node has no downstream impact."""
    tracker = _make_tracker([("A", "B")])
    result = tracker.get_downstream_impact("B", depth=5)
    assert result == []


def test_downstream_impact_cycle_does_not_loop():
    """A -> B -> A (cycle): BFS must terminate without infinite loop."""
    tracker = _make_tracker([("A", "B"), ("B", "A")])
    result = tracker.get_downstream_impact("A", depth=10)
    # Should not raise or hang; B should appear, A should not re-appear
    assert "B" in result
    assert result.count("B") == 1


def test_downstream_impact_node_order():
    """BFS should discover nodes breadth-first (siblings before children)."""
    # A -> B, A -> C, B -> D
    tracker = _make_tracker([("A", "B"), ("A", "C"), ("B", "D")])
    result = tracker.get_downstream_impact("A", depth=5)
    # B and C (depth 1) must appear before D (depth 2)
    assert result.index("B") < result.index("D")
    assert result.index("C") < result.index("D")


# ---------------------------------------------------------------------------
# Tests: get_upstream_lineage (BFS upstream)
# ---------------------------------------------------------------------------

def test_upstream_lineage_direct_parents():
    """A -> C and B -> C: upstream of C should include A and B."""
    tracker = _make_tracker([("A", "C"), ("B", "C")])
    result = tracker.get_upstream_lineage("C", depth=1)
    assert set(result) == {"A", "B"}


def test_upstream_lineage_multi_hop():
    """A -> B -> C: upstream of C at depth 2 should include both B and A."""
    tracker = _make_tracker([("A", "B"), ("B", "C")])
    result = tracker.get_upstream_lineage("C", depth=2)
    assert "B" in result
    assert "A" in result


def test_upstream_lineage_no_parents():
    """Root node has no upstream sources."""
    tracker = _make_tracker([("A", "B")])
    result = tracker.get_upstream_lineage("A", depth=5)
    assert result == []


# ---------------------------------------------------------------------------
# Tests: upsert_node and record_edge (writes)
# ---------------------------------------------------------------------------

def test_upsert_node_writes_to_es():
    es = _FakeES([])
    tracker = LineageTracker(es)

    node = LineageNode(
        node_id="rds.prod.orders",
        node_type=NodeType.TABLE,
        name="orders",
        platform="aws",
        environment="production",
        owner="data-team",
    )
    tracker.upsert_node(node)

    assert "rds.prod.orders" in es._nodes


def test_record_edge_writes_to_indexed_docs():
    es = _FakeES([])
    tracker = LineageTracker(es)

    edge = LineageEdge(
        source_node_id="rds.prod.source",
        target_node_id="rds.prod.target",
        job_id="glue-job-1",
        job_type="glue_job",
    )
    tracker.record_edge(edge)

    assert len(es.indexed_docs) == 1
    doc = es.indexed_docs[0]["doc"]
    assert doc["source_node_id"] == "rds.prod.source"
    assert doc["target_node_id"] == "rds.prod.target"
