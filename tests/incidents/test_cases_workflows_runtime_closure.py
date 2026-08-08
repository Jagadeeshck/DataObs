from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest

from packages.elastic_store.manifest import BASE_PROPERTIES, INCIDENT_AUTOMATION_PROPERTIES
from services.incident_manager.automation.contracts import Execution, ExecutionState
from services.incident_manager.automation.execution import ExecutionWorker, ExecutorRegistry
from services.incident_manager.automation.repository import InMemoryAutomationRepository
from services.incident_manager.automation.targets import ActionTarget, BoundedActionTargetResolver
from services.incident_manager.cases.contracts import CaseLink, CaseLinkState
from services.incident_manager.cases.repository import (
    ElasticsearchCaseRepository,
    InMemoryCaseLinkRepository,
    _document,
)


def link(state: CaseLinkState = CaseLinkState.CREATE_RESERVED) -> CaseLink:
    return CaseLink(
        link_id="dataobs-ref-1",
        tenant_id="tenant",
        environment="prod",
        incident_id="incident",
        kibana_space="dataobs",
        reconciliation_reference="dataobs-ref-1",
        creation_actor="actor",
        request_id="request",
        state=state,
    )


def test_case_link_document_uses_only_mapped_fields() -> None:
    document = _document(link())
    assert set(document) <= set(BASE_PROPERTIES) | set(INCIDENT_AUTOMATION_PROPERTIES)
    assert "case_link_id" not in document and "case_id" not in document


def test_case_reservation_document_matches_strict_mapping() -> None:
    document = _document(link())
    assert all(name in (BASE_PROPERTIES | INCIDENT_AUTOMATION_PROPERTIES) for name in document)


def test_remote_case_id_uses_elastic_case_id() -> None:
    item = link(CaseLinkState.LINKED).model_copy(update={"elastic_case_id": "remote-1"})
    assert _document(item)["elastic_case_id"] == "remote-1"


def test_case_repository_round_trip() -> None:
    original = link()
    restored = CaseLink.model_validate(_document(original)["metadata"])
    assert restored == original
    assert isinstance(restored.state, CaseLinkState)


def test_concurrent_case_reservation_is_singleton() -> None:
    repository = InMemoryCaseLinkRepository()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(repository.reserve, (link(), link())))
    assert results[0] == results[1]
    assert len(repository._items) == 1


class StateRepository(ElasticsearchCaseRepository):
    def __init__(self):
        pass

    def update_link_occ(self, item, expected_revision):
        item.revision = expected_revision + 1
        _document(item)  # strict serialization must continue to work
        return item


@pytest.mark.parametrize(
    ("start", "method", "expected"),
    [
        (CaseLinkState.CREATE_RESERVED, "mark_submitted", CaseLinkState.CREATE_SUBMITTED),
        (CaseLinkState.CREATE_RESERVED, "mark_reconciliation_required", CaseLinkState.CREATE_RECONCILIATION_REQUIRED),
        (CaseLinkState.LINKED, "mark_sync_required", CaseLinkState.SYNC_REQUIRED),
        (CaseLinkState.SYNC_REQUIRED, "mark_synced", CaseLinkState.SYNCED),
        (CaseLinkState.SYNC_REQUIRED, "mark_sync_failed", CaseLinkState.SYNC_FAILED),
        (CaseLinkState.LINKED, "mark_remote_missing", CaseLinkState.REMOTE_MISSING),
    ],
)
def test_case_repository_state_helpers_preserve_enum(start, method, expected) -> None:
    result = getattr(StateRepository(), method)(link(start))
    assert result.state is expected
    assert isinstance(result.state, CaseLinkState)


def test_case_repository_mark_linked_preserves_enum() -> None:
    result = StateRepository().mark_linked(link(), "remote")
    assert result.state is CaseLinkState.LINKED
    assert _document(result)["elastic_case_id"] == "remote"


def test_illegal_case_transition_fails_closed() -> None:
    with pytest.raises(Exception, match="illegal case link transition"):
        StateRepository()._mark(link(CaseLinkState.LINKED), CaseLinkState.CREATE_RESERVED)


class Sources:
    def __init__(self, references):
        self.references = references

    def relevant_finding_references(self, tenant_id, environment, incident_id, limit):
        return self.references[:limit]

    def get_finding(self, tenant_id, environment, reference):
        return {"scanner_id": reference}

    def get_target(self, tenant_id, environment, target_type, target_id):
        return ActionTarget(target_type, target_id, "1")


def test_one_candidate_at_candidate_limit_resolves() -> None:
    source = Sources(["one"])
    result = BoundedActionTargetResolver(source, source, source, max_candidates=1).resolve(
        tenant_id="t", environment="e", incident_id="i", action_type="rerun_scan"
    )
    assert result.status == "resolved" and not result.truncated


def test_actual_truncation_is_reported() -> None:
    source = Sources(["one", "two"])
    result = BoundedActionTargetResolver(source, source, source, max_candidates=1).resolve(
        tenant_id="t", environment="e", incident_id="i", action_type="rerun_scan"
    )
    assert result.status == "selection_required" and result.truncated


def test_incomplete_resolution_does_not_claim_unique_target() -> None:
    source = Sources(["one", "two"])
    result = BoundedActionTargetResolver(source, source, source, max_candidates=1).resolve(
        tenant_id="t", environment="e", incident_id="i", action_type="rerun_scan"
    )
    assert result.target is None and result.reason_codes == ("incomplete_resolution",)


def execution(start):
    return Execution(
        execution_id="x",
        tenant_id="t",
        environment="e",
        incident_id="i",
        action_type="rerun_scan",
        state=ExecutionState.RUNNING,
        request_id="r",
        actor="a",
        action_fingerprint="f",
        catalogue_hash="c",
        policy_hash="p",
        incident_revision="1",
        preview_id="v",
        approval_id=None,
        payload_fingerprint="p",
        target={"type": "scanner", "id": "s", "revision": "1"},
        lease_owner="worker",
        lease_token=1,
        lease_expires_at=start,
        created_at=start,
        updated_at=start,
        execution_started_at=start,
        timeout_seconds=1,
        max_attempts=1,
    )


def test_heartbeat_stops_at_execution_timeout() -> None:
    repo = InMemoryAutomationRepository()
    item = execution(datetime.now(timezone.utc) - timedelta(seconds=2))
    repo.executions[item.execution_id] = item
    lost = Event()
    ExecutionWorker(repo, ExecutorRegistry(), "worker", lease_seconds=3, heartbeat_seconds=0.01)._heartbeat(
        item, Event(), lost
    )
    assert lost.is_set()
    assert repo.executions[item.execution_id].lease_expires_at == item.lease_expires_at
