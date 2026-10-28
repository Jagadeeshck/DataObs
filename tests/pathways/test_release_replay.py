from copy import deepcopy
from datetime import datetime, timezone

import pytest

from packages.pathways.intelligence import assemble_pathways, canonical_edge, canonical_node, pathway_health
from services.pathway_worker.checkpoint_store import EventWatermark
from services.pathway_worker.repository import ElasticsearchPathwayRepository
from services.pathway_worker.service import PathwayWorkerService


def test_late_replay_does_not_regress_event_watermark():
    cp = EventWatermark("t", "prod").committed("2026-10-28T10:00:00+00:00", "b", 1, "old", 1)
    late = cp.committed("2026-10-28T09:59:00+00:00", "z", 1, "new", 2)
    assert late.position() == cp.position()
    assert late.fencing_token == 2
    assert late.documents_processed == 2


def test_bounded_graph_is_deterministic_across_order_and_scope():
    def graph(tenant="t", environment="prod"):
        nodes = [canonical_node(tenant, environment, "service", name) for name in "abcd"]
        edges = [
            canonical_edge(tenant, environment, nodes[0]["node_id"], n["node_id"], "dependency") for n in nodes[1:]
        ]
        return nodes, edges

    nodes, edges = graph()
    first = assemble_pathways(nodes, edges, max_edges=2)
    assert first == assemble_pathways(nodes[::-1], edges[::-1], max_edges=2)
    assert first != assemble_pathways(*graph("other"), max_edges=2)
    assert first != assemble_pathways(*graph(environment="stage"), max_edges=2)
    assert len(assemble_pathways(nodes, edges, max_pathways=1)) == 1
    with pytest.raises(ValueError):
        assemble_pathways(nodes, edges, max_hops=10_000)
    assert pathway_health([{"health": "healthy"}, {}])["health"] == "unknown"
    assert pathway_health([{"health": "healthy"}], stale=True)["health"] == "unknown"


class Repository:
    max_documents = 2
    tenant_id, environment = "t", "prod"

    def __init__(self):
        self.cp = {}
        self.fail = True
        self.nodes, self.edges = {}, {}
        self.calls = []

    def acquire_lease(self, worker):
        return 2

    def release_lease(self, worker, token):
        self.calls.append("release")

    def checkpoint(self):
        return deepcopy(self.cp)

    def read_spans(self, *, after, since, size):
        self.calls.append(("read", after))
        rows = [
            {
                "@timestamp": "2026-10-28T10:00:00+00:00",
                "service.name": "billing",
                "trace_id": "trace",
                "messaging.system": "kafka",
                "messaging.destination.name": "orders",
                "messaging.operation.type": "send",
                "_source_document_id": str(i),
            }
            for i in (range(2) if after is None else range(2, 3))
        ]
        return rows, ["2026-10-28T10:00:00+00:00", rows[-1]["_source_document_id"]]

    def save(self, edges, position, worker, token, count, *, nodes, pathways, scan_position):
        self.edges.update({e["edge_id"]: e for e in edges})
        self.nodes.update({n["node_id"]: n for n in nodes})
        if self.fail:
            self.fail = False
            raise RuntimeError("projection succeeded; checkpoint failed")
        self.cp = {"last_event_timestamp": position[0], "last_event_id": position[1], "scan_position": scan_position}
        self.calls.append("checkpoint")


def test_restart_after_projection_failure_replays_identity_then_resumes_full_page():
    repo = Repository()
    with pytest.raises(RuntimeError):
        PathwayWorkerService(repo, worker_id="one").process_once()
    identities = (set(repo.nodes), set(repo.edges))
    assert repo.cp == {} and repo.calls[-1] == "release"
    restarted = PathwayWorkerService(repo, worker_id="two")
    restarted.process_once()
    assert (set(repo.nodes), set(repo.edges)) == identities
    position = repo.cp["scan_position"]
    assert position is not None
    restarted.process_once()
    assert ("read", position) in repo.calls
    assert repo.cp["last_event_id"] == "2" and repo.cp["scan_position"] is None


def test_worker_source_and_page_bounds_are_fail_closed():
    for sources in (["*"], ["dataobs-*"], ["traces-apm-*,private-index"], []):
        with pytest.raises(ValueError):
            ElasticsearchPathwayRepository(object(), "t", "prod", sources)
    repo = ElasticsearchPathwayRepository(object(), "t", "prod", ["traces-apm-*"])
    for size in (0, -1, 2001):
        with pytest.raises(ValueError):
            repo.read_spans(after=None, since=datetime.now(timezone.utc).isoformat(), size=size)
