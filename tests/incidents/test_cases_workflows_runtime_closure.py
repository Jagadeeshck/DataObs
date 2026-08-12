import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import pytest

from packages.elastic_store.manifest import BASE_PROPERTIES, INCIDENT_AUTOMATION_PROPERTIES
from services.data_products.cursors import InvalidCursor
from services.incident_manager.automation.contracts import Execution, ExecutionResult, ExecutionState
from services.incident_manager.automation.execution import ExecutionWorker, ExecutorRegistry
from services.incident_manager.automation.repository import InMemoryAutomationRepository
from services.incident_manager.automation.targets import (
    ActionTarget,
    BoundedActionTargetResolver,
    TargetAuthorityRegistry,
    TargetSelectionCodec,
)
from services.incident_manager.cases.contracts import CaseLink, CaseLinkState
from services.incident_manager.cases.repository import (
    ElasticsearchCaseRepository,
    InMemoryCaseLinkRepository,
    _document,
)
from src.api.incident_automation_routes import ExecutionRequestBody


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


def test_server_candidate_selection_can_proceed_and_is_scope_bound() -> None:
    candidates = (ActionTarget("scanner", "one", "1"), ActionTarget("scanner", "two", "2"))
    codec = TargetSelectionCodec(b"selection-test-secret-that-is-long-enough")
    selection = codec.issue(
        tenant_id="tenant",
        environment="prod",
        incident_id="incident",
        action_type="rerun_scan",
        candidates=candidates,
        candidate=candidates[1],
    )
    assert (
        codec.select(
            selection,
            tenant_id="tenant",
            environment="prod",
            incident_id="incident",
            action_type="rerun_scan",
            candidates=candidates,
        ).target_id
        == "two"
    )
    for changed in (
        {"tenant_id": "other"},
        {"environment": "staging"},
        {"incident_id": "other"},
        {"action_type": "connection_test"},
    ):
        scope = {
            "tenant_id": "tenant",
            "environment": "prod",
            "incident_id": "incident",
            "action_type": "rerun_scan",
            "candidates": candidates,
            **changed,
        }
        with pytest.raises(InvalidCursor):
            codec.select(selection, **scope)


def test_arbitrary_and_stale_server_candidates_are_rejected() -> None:
    candidates = (ActionTarget("scanner", "one", "1"), ActionTarget("scanner", "two", "2"))
    codec = TargetSelectionCodec(b"selection-test-secret-that-is-long-enough")
    selection = codec.issue(
        tenant_id="tenant",
        environment="prod",
        incident_id="incident",
        action_type="rerun_scan",
        candidates=candidates,
        candidate=candidates[0],
    )
    with pytest.raises(InvalidCursor):
        codec.select(
            selection[:-2] + "xx",
            tenant_id="tenant",
            environment="prod",
            incident_id="incident",
            action_type="rerun_scan",
            candidates=candidates,
        )
    with pytest.raises(InvalidCursor):
        codec.select(
            selection,
            tenant_id="tenant",
            environment="prod",
            incident_id="incident",
            action_type="rerun_scan",
            candidates=(candidates[1],),
        )


def test_incident_target_uses_incident_repository_and_bypasses_capability_reader() -> None:
    class Incidents:
        def get_target(self, tenant_id, environment, target_type, target_id):
            return ActionTarget("incident", target_id, "8:2")

    class Capabilities:
        def get_target(self, *args):
            raise AssertionError("incident must not reach capability authority")

    registry = TargetAuthorityRegistry(Incidents(), Capabilities())
    assert registry.get_target("t", "e", "incident", "i").revision == "8:2"
    assert registry.get_target("t", "e", "unknown", "i") is None


class AcceptingExecutor:
    action_type = "rerun_scan"
    cancellation_supported = False

    def execute(self, item):
        return ExecutionResult(True, False, "operation")


def _queued(execution_id: str, now: datetime) -> Execution:
    item = execution(now).model_copy(
        update={
            "execution_id": execution_id,
            "state": ExecutionState.QUEUED,
            "lease_owner": None,
            "lease_token": 0,
            "execution_started_at": None,
            "queued_at": now,
            "timeout_seconds": 10,
        }
    )
    return item


def test_each_batch_item_gets_own_execution_start_and_full_timeout() -> None:
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    times = iter(
        [
            start + timedelta(seconds=1),  # first claim
            start + timedelta(seconds=2),  # first execution start
            start + timedelta(seconds=3),  # first completion
            start + timedelta(seconds=8),  # second claim (queue wait)
            start + timedelta(seconds=9),  # second execution start
            start + timedelta(seconds=10),  # second completion
        ]
    )
    repo = InMemoryAutomationRepository()
    repo.executions = {"one": _queued("one", start), "two": _queued("two", start)}
    worker = ExecutionWorker(
        repo,
        ExecutorRegistry((AcceptingExecutor(),)),
        "worker",
        lease_seconds=30,
        heartbeat_seconds=10,
        clock=lambda: next(times),
    )
    assert worker.run_once(now=start) == 2
    assert repo.executions["one"].execution_started_at == start + timedelta(seconds=2)
    assert repo.executions["two"].execution_started_at == start + timedelta(seconds=9)
    assert repo.executions["two"].state == ExecutionState.VERIFICATION_PENDING


def test_late_executor_result_cannot_commit_success_and_requires_reconciliation() -> None:
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    times = iter([start, start, start + timedelta(seconds=11)])
    repo = InMemoryAutomationRepository()
    repo.executions = {"late": _queued("late", start)}
    worker = ExecutionWorker(
        repo,
        ExecutorRegistry((AcceptingExecutor(),)),
        "worker",
        lease_seconds=30,
        heartbeat_seconds=10,
        clock=lambda: next(times),
    )
    assert worker.run_once(now=start) == 1
    late = repo.executions["late"]
    assert late.state == ExecutionState.RECONCILIATION_REQUIRED
    assert late.error_code == "execution_deadline_exceeded"
    assert late.operation_reference is None


def test_case_repository_never_sorts_on_id_and_sort_is_deterministic() -> None:
    class Client:
        def search(self, **kwargs):
            self.request = kwargs
            return {"hits": {"hits": []}}

    client = Client()
    ElasticsearchCaseRepository(client).search_links("tenant", "prod", "space")
    assert client.request["sort"] == [
        {"updated_at": {"order": "asc", "missing": "_first"}},
        {"incident_id": "asc"},
    ]
    assert all("_id" not in clause for clause in client.request["sort"])


def test_execution_openapi_matches_request_model() -> None:
    document = json.loads(Path("openapi.json").read_text())
    generated = document["components"]["schemas"]["ExecutionRequestBody"]
    runtime = ExecutionRequestBody.model_json_schema()
    assert generated["required"] == runtime["required"] == ["preview_id"]
    assert set(generated["properties"]) == set(runtime["properties"]) == {"preview_id", "approval_id"}
    assert "incident_revision" not in generated["properties"]
    assert "target_revision" not in generated["properties"]
