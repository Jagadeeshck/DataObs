from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from packages.domain_model.incident import Finding, FindingType, Incident, SignalType
from services.incident_manager.elasticsearch_repository import ElasticsearchIncidentRepository
from services.incident_manager.repository import InMemoryIncidentRepository, VersionConflict
from services.incident_manager.service import IncidentManagerService, decide_finding_merge, incident_id, merge_finding


def _incident(**kwargs):
    return Incident(id="i1", tenant_id="t1", environment="prod", deduplication_key="d1", **kwargs)


def _finding(fid="f1", asset="a1", **kwargs):
    now = kwargs.pop("last_observed_at", datetime.now(timezone.utc))
    return Finding(
        id=fid,
        tenant_id="t1",
        environment="prod",
        finding_type=FindingType.SCHEMA_CHANGE,
        signal_type=SignalType.POSTGRES_SCHEMA_CHANGE,
        source_event_id=fid,
        asset_id=asset,
        title="change",
        summary="change",
        first_observed_at=now,
        last_observed_at=now,
        **kwargs,
    )


def test_merge_finding_is_pure_and_idempotent():
    original = _incident(finding_ids=["f1"], occurrence_count=1, affected_assets=["a1"])
    replay = merge_finding(original, _finding())
    assert replay.occurrence_count == 1
    assert original.occurrence_count == 1
    merged = merge_finding(replay, _finding("f2", "a2"))
    assert merged.occurrence_count == 2
    assert merged.finding_ids == ["f1", "f2"]
    assert merged.affected_assets == ["a1", "a2"]


def test_dedup_search_is_environment_scoped_and_requests_occ():
    client = MagicMock()
    client.search.return_value = {"hits": {"hits": []}}
    ElasticsearchIncidentRepository(client).find_incident_by_dedup("t1", "prod", "d1")
    call = client.search.call_args.kwargs
    assert call["seq_no_primary_term"] is True
    assert call["query"]["bool"]["filter"] == [
        {"term": {"tenant_id": "t1"}},
        {"term": {"environment": "prod"}},
        {"term": {"deduplication_key": "d1"}},
    ]


def test_incident_list_search_requests_occ():
    client = MagicMock()
    client.search.return_value = {"hits": {"hits": []}}
    ElasticsearchIncidentRepository(client).list_incidents("t1", "prod")
    assert client.search.call_args.kwargs["seq_no_primary_term"] is True


def test_update_requires_occ_and_create_is_create_only():
    client = MagicMock()
    client.index.return_value = {"_seq_no": 0, "_primary_term": 1}
    repo = ElasticsearchIncidentRepository(client)
    with pytest.raises(VersionConflict):
        repo.update_incident(_incident())
    repo.create_incident(_incident())
    assert client.index.call_args.kwargs["op_type"] == "create"


def test_incident_id_matches_pre_0012_contract():
    from packages.domain_model.incident import deterministic_id

    assert incident_id("tenant-a", "dedup-with-environment") == deterministic_id(
        "incident", ["tenant-a", "dedup-with-environment"]
    )


def test_exact_and_stale_replays_are_noops():
    now = datetime.now(timezone.utc)
    incident = _incident(
        finding_ids=["f1"],
        affected_assets=["a1"],
        occurrence_count=1,
        last_observed_at=now,
    )
    exact = decide_finding_merge(incident, _finding(last_observed_at=now))
    stale = decide_finding_merge(incident, _finding(last_observed_at=now - timedelta(minutes=1)))
    assert (exact.changed, exact.reason, exact.incident is incident) == (False, "exact_replay", True)
    assert (stale.changed, stale.reason, stale.occurrence_added) == (False, "stale_replay", False)


def test_newer_replay_refreshes_projection_without_occurrence():
    now = datetime.now(timezone.utc)
    incident = _incident(
        finding_ids=["f1"],
        affected_assets=["a1"],
        occurrence_count=1,
        last_observed_at=now,
        most_recent_evidence=[{"old": True}],
    )
    decision = decide_finding_merge(
        incident,
        _finding(last_observed_at=now + timedelta(minutes=1), evidence=[{"new": True}], downstream_impact=["a2"]),
    )
    assert decision.reason == "newer_replay"
    assert decision.occurrence_added is False
    assert decision.incident.occurrence_count == 1
    assert decision.incident.affected_assets == ["a1", "a2"]
    assert decision.incident.most_recent_evidence == [{"new": True}]


def test_stale_replay_can_only_enrich_assets():
    now = datetime.now(timezone.utc)
    incident = _incident(
        finding_ids=["f1"],
        affected_assets=["a1"],
        last_observed_at=now,
        most_recent_evidence=[{"new": True}],
    )
    decision = decide_finding_merge(
        incident,
        _finding(last_observed_at=now - timedelta(minutes=1), evidence=[{"old": True}], downstream_impact=["a2"]),
    )
    assert decision.reason == "projection_enrichment"
    assert decision.incident.affected_assets == ["a1", "a2"]
    assert decision.incident.most_recent_evidence == [{"new": True}]
    assert decision.incident.last_observed_at == now


class RecordingRepository(InMemoryIncidentRepository):
    def __init__(self):
        super().__init__()
        self.create_calls = 0
        self.update_calls = 0
        self.conflicts = 0
        self.sequence_changes = []

    def create_incident(self, incident):
        self.create_calls += 1
        return super().create_incident(incident)

    def update_incident(self, incident):
        self.update_calls += 1
        before = self.incidents[incident.id].seq_no
        result = super().update_incident(incident)
        self.sequence_changes.append((before, result.seq_no))
        return result


def test_exact_replay_performs_zero_updates_and_preserves_sequence():
    repo = RecordingRepository()
    service = IncidentManagerService(repo)
    event = {
        "id": "event-1",
        "tenant_id": "t1",
        "environment": "prod",
        "asset_id": "a1",
        "observed_at": "2026-01-01T00:00:00Z",
    }
    first = service.ingest(event, tenant_id="t1")
    updated_at = first["incident"]["updated_at"]
    replay = service.ingest(event, tenant_id="t1")
    assert replay["ingestion"] == {
        "status": "replayed",
        "reason": "exact_replay",
        "occurrence_added": False,
        "incident_changed": False,
    }
    assert repo.update_calls == 0
    assert replay["incident"]["seq_no"] == 0
    assert replay["incident"]["updated_at"] == updated_at
