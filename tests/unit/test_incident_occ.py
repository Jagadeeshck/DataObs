from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from packages.domain_model.incident import Finding, FindingType, Incident, SignalType
from services.incident_manager.elasticsearch_repository import ElasticsearchIncidentRepository
from services.incident_manager.repository import VersionConflict
from services.incident_manager.service import merge_finding


def _incident(**kwargs):
    return Incident(id="i1", tenant_id="t1", environment="prod", deduplication_key="d1", **kwargs)


def _finding(fid="f1", asset="a1"):
    now = datetime.now(timezone.utc)
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
