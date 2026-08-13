from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.slo import EvidenceClassification, IntervalEvidence
from services.data_slo.models import RuntimeState
from services.data_slo.repository import DefinitionConflict, FenceLost, MemoryDataSLORepository
from services.data_slo.runtime import DataSLORuntime
from services.data_slo.service import DataSLOService

NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


def payload():
    return {
        "id": "freshness",
        "scope_type": "asset",
        "scope_id": "a1",
        "name": "Freshness",
        "sli_type": "freshness",
        "objective": 0.99,
        "window": "1h",
        "evaluation_granularity": "5m",
        "source_monitor_ids": ["m1"],
        "owner_team": "quality",
    }


def test_lifecycle_occ_revision_and_tenant_isolation():
    repo = MemoryDataSLORepository()
    service = DataSLOService(repo)
    value = service.create_definition(payload(), tenant_id="a", environment="prod", actor="user:1", reason="new SLO")
    assert repo.get_definition("b", "prod", value.id) is None
    with pytest.raises(DefinitionConflict):
        service.transition("a", "prod", value.id, "active", actor="user:1", reason="activate", expected_etag="stale")
    active = service.transition(
        "a", "prod", value.id, "active", actor="user:1", reason="activate", expected_etag=value.etag
    )
    assert active.revision == 2 and len(repo.list_revisions("a", "prod", value.id, limit=10)) == 2


class Resolver:
    def resolve(self, definition, start, end):
        return [
            IntervalEvidence(classification=EvidenceClassification.GOOD, evidence_ref=f"monitor:m1:{n}")
            for n in range(997)
        ] + [
            IntervalEvidence(classification=EvidenceClassification.BAD, evidence_ref=f"monitor:m1:b{n}")
            for n in range(3)
        ]


def test_runtime_replay_and_fence_takeover():
    repo = MemoryDataSLORepository()
    service = DataSLOService(repo)
    draft = service.create_definition(payload(), tenant_id="a", environment="prod", actor="u", reason="create")
    active = service.transition("a", "prod", draft.id, "active", actor="u", reason="activate", expected_etag=draft.etag)
    repo.seed_runtime(RuntimeState("a", "prod", active.id, NOW - timedelta(minutes=1)))
    result = DataSLORuntime(repo, Resolver(), worker_id="one").evaluate_due("a", "prod", now=NOW)
    assert result[0].state == "healthy" and result[0].budget.budget_remaining > 0
    assert repo.append_evaluation(result[0]) is False
    old_token = repo.runtime[("a", "prod", active.id)].fencing_token
    state = repo.runtime[("a", "prod", active.id)]
    repo.runtime[("a", "prod", active.id)] = state.__class__(
        **{**state.__dict__, "lease_expires_at": NOW - timedelta(seconds=1)}
    )
    assert repo.acquire_lease("a", "prod", active.id, "two", NOW, NOW + timedelta(seconds=30)) > old_token
    with pytest.raises(FenceLost):
        repo.put_current(result[0], fencing_token=old_token)
