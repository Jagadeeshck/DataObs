from datetime import datetime, timedelta, timezone

from packages.pathways.investigation import HistoricalEdge, HistoricalNode
from services.pathway_worker.history_projector import HistoryProjector


class Store:
    snapshots = []

    def latest_snapshot(self, pathway_id):
        return self.snapshots[-1] if self.snapshots else None

    def persist_snapshot(self, snapshot, fencing_token):
        assert fencing_token == 7
        self.snapshots.append(snapshot)


def test_forward_only_changed_graph_snapshots() -> None:
    store = Store()
    projector = HistoryProjector(store, "t1", "prod")
    now = datetime.now(timezone.utc)
    nodes = [HistoricalNode("A", "topic"), HistoricalNode("B", "consumer")]
    first = projector.materialize(
        "p", nodes, [HistoricalEdge("ab", "A", "B", "consumed_by")], effective_at=now, fencing_token=7
    )
    assert first and first.change_reason_codes == ("first_observation",)
    assert (
        projector.materialize(
            "p",
            nodes,
            [HistoricalEdge("ab", "A", "B", "consumed_by", confidence=0.1)],
            effective_at=now + timedelta(minutes=1),
            fencing_token=7,
        )
        is None
    )
    changed = projector.materialize(
        "p",
        nodes + [HistoricalNode("C", "topic")],
        [HistoricalEdge("ac", "A", "C", "flows_to")],
        effective_at=now + timedelta(minutes=2),
        fencing_token=7,
    )
    assert changed and changed.graph_hash != first.graph_hash
