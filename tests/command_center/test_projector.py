"""Unit tests for the ES-backed Command Center projector with a fake client.

Validates tenant-scoped reads, honest source-availability tracking (missing index →
source unavailable → summary not complete), and that the summary is written to the
correct write alias/doc id.
"""

from __future__ import annotations

from services.command_center.projector import WRITE_INDEX, CommandCenterProjector


class _FakeES:
    def __init__(self, responses: dict, missing: set[str] | None = None):
        # responses: index -> list of _source docs
        self._responses = responses
        self._missing = missing or set()
        self.indexed: list[dict] = []

    def search(self, index, query=None, size=0, aggs=None, **kwargs):
        if index in self._missing:
            raise RuntimeError(f"index_not_found_exception: {index}")
        docs = self._responses.get(index, [])
        return {"hits": {"hits": [{"_source": d} for d in docs]}}

    def index(self, index, id, document, refresh=False):
        self.indexed.append({"index": index, "id": id, "document": document})
        return {"result": "created"}


def test_project_writes_summary_to_correct_alias_and_id():
    es = _FakeES(
        {
            "dataobs-incidents-v1-read": [
                {"incident_id": "inc-1", "severity": "critical", "state": "open", "entity": "orders"}
            ],
            "dataobs-quality-current-v1-read": [{"status": "pass"}],
            "dataobs-freshness-current-v1-read": [{"status": "fresh"}],
            "dataobs-lineage-current-v1-read": [{"id": "e1"}],
            "dataobs-stream-clusters-v1-read": [{"health": "healthy"}],
        }
    )
    summary = CommandCenterProjector(es).project("acme", "production")

    assert len(es.indexed) == 1
    written = es.indexed[0]
    assert written["index"] == WRITE_INDEX
    assert written["id"] == "acme:production"
    assert summary["data_status"]["complete"] is True
    assert summary["critical_incidents"] == 1


def test_missing_source_marks_incomplete_and_pillar_unknown():
    es = _FakeES(
        {
            "dataobs-incidents-v1-read": [],
            "dataobs-quality-current-v1-read": [{"status": "pass"}],
            "dataobs-freshness-current-v1-read": [],
            "dataobs-lineage-current-v1-read": [],
        },
        missing={"dataobs-stream-clusters-v1-read"},  # streams index absent
    )
    summary = CommandCenterProjector(es).project("acme", "production")

    assert summary["data_status"]["complete"] is False
    assert "streams" in summary["data_status"]["missing_inputs"]
    platform = next(p for p in summary["pillars"] if p["id"] == "platform")
    assert platform["health"] == "unknown"  # no stream source → not healthy


def test_reads_are_tenant_and_environment_scoped():
    captured = {}

    class _CapturingES(_FakeES):
        def search(self, index, query=None, size=0, aggs=None, **kwargs):
            captured[index] = query
            return super().search(index, query=query, size=size, aggs=aggs, **kwargs)

    es = _CapturingES(
        {
            k: []
            for k in [
                "dataobs-incidents-v1-read",
                "dataobs-quality-current-v1-read",
                "dataobs-freshness-current-v1-read",
                "dataobs-lineage-current-v1-read",
                "dataobs-stream-clusters-v1-read",
            ]
        }
    )
    CommandCenterProjector(es).project("tenant-x", "staging")
    for index, query in captured.items():
        filters = query["bool"]["filter"]
        assert {"term": {"tenant_id": "tenant-x"}} in filters
        assert {"term": {"environment": "staging"}} in filters
