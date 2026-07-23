"""Executed, scoped persistence controls against the certification cluster."""

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.operation_state import (
    DataProductOperationHistoryEvent,
    DataProductOperationPlan,
    DataProductOperationResultEnvelope,
    DataProductOperationState,
    OperationClaimConflict,
)
from services.data_products.reconciliation import _checksum


def _sha():
    return os.getenv("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def test_foundation_persistence_isolation_controls(security_client, security_evidence_dir, executed_control):
    started = datetime.now(timezone.utc)
    repository = ElasticsearchDataProductRepository(security_client)
    suffix, operation_id = uuid4().hex, "shared-operation"
    tenant_a, tenant_b = f"tenant-a-{suffix}", f"tenant-b-{suffix}"
    scopes = ((tenant_a, "prod"), (tenant_b, "prod"), (tenant_a, "stage"))
    for tenant, environment in scopes:
        payload = {"tenant": tenant, "environment": environment}
        plan = DataProductOperationPlan(
            f"plan:{tenant}:{environment}",
            tenant,
            environment,
            suffix,
            operation_id,
            "manual_membership",
            _checksum(payload),
            payload,
        )
        repository.save_operation_plan(plan)
        repository.save_operation_result(
            DataProductOperationResultEnvelope(
                f"result:{tenant}:{environment}",
                tenant,
                environment,
                suffix,
                operation_id,
                _checksum(payload),
                payload,
                started,
            )
        )
        repository.append_operation_history(
            DataProductOperationHistoryEvent(
                f"event-{tenant}-{environment}",
                operation_id,
                tenant,
                environment,
                suffix,
                "manual_membership",
                "manual_membership",
                "pending",
                "certifier",
                "isolation",
                _checksum(payload),
                started,
            )
        )
        repository.create_operation_state(
            DataProductOperationState(
                operation_id,
                tenant,
                environment,
                suffix,
                "manual_membership",
                "pending",
                0,
                started,
                plan_reference=plan.reference,
            )
        )
    assert repository.get_operation_state(tenant_a, "prod", operation_id).tenant_id == tenant_a
    assert repository.get_operation_state(tenant_b, "prod", operation_id).tenant_id == tenant_b
    assert repository.get_operation_state(tenant_a, "stage", operation_id).environment == "stage"
    assert repository.get_operation_state("wrong", "prod", operation_id) is None
    assert repository.load_operation_plan(tenant_a, "prod", suffix, operation_id).tenant_id == tenant_a
    assert repository.load_operation_plan("wrong", "prod", suffix, operation_id) is None
    assert repository.load_operation_result(tenant_a, "prod", suffix, operation_id).tenant_id == tenant_a
    assert repository.load_operation_result("wrong", "prod", suffix, operation_id) is None
    assert [event.tenant_id for event in repository.get_operation_history(tenant_a, "prod", operation_id)] == [tenant_a]
    assert repository.get_operation_history("wrong", "prod", operation_id) == []
    selected = repository.list_reconcilable_operations(tenant_a, "prod", now=started + timedelta(seconds=1))
    assert [state.tenant_id for state in selected if state.operation_id == operation_id] == [tenant_a]
    assert repository.list_reconcilable_operations("wrong", "prod", now=started + timedelta(seconds=1)) == []
    scoped = repository.get_operation_state(tenant_a, "prod", operation_id)
    before_history = repository.get_operation_history(tenant_a, "prod", operation_id)
    for wrong_tenant, wrong_environment in ((f"wrong-{tenant_a}", "prod"), (tenant_a, "wrong-environment")):
        with pytest.raises(KeyError, match=operation_id):
            repository.claim_operation(
                wrong_tenant,
                wrong_environment,
                operation_id,
                worker_id="wrong-scope-worker",
                now=started,
                expires_at=started + timedelta(minutes=1),
                expected_seq_no=scoped.seq_no,
                expected_primary_term=scoped.primary_term,
            )
    unchanged = repository.get_operation_state(tenant_a, "prod", operation_id)
    assert (unchanged.claim_owner, unchanged.claim_generation, unchanged.last_checkpoint) == (None, 0, None)
    assert repository.get_operation_history(tenant_a, "prod", operation_id) == before_history
    claim = repository.claim_operation(
        tenant_a,
        "prod",
        operation_id,
        worker_id="correct-scope-worker",
        now=started,
        expires_at=started + timedelta(minutes=1),
        expected_seq_no=unchanged.seq_no,
        expected_primary_term=unchanged.primary_term,
    )
    assert claim.owner == "correct-scope-worker" and claim.generation == 1
    controls = [
        executed_control(
            "cross_tenant_state_isolation", "tenant_a_state_read", "tenant_b_state_read", "wrong_tenant_state_absent"
        ),
        executed_control("cross_environment_state_isolation", "production_state_read", "stage_state_read"),
        executed_control("same_operation_id_scope_isolation", "same_id_tenant_a", "same_id_tenant_b", "same_id_stage"),
        executed_control("cross_tenant_plan_isolation", "correct_plan_read", "wrong_tenant_plan_absent"),
        executed_control("cross_tenant_result_isolation", "correct_result_read", "wrong_tenant_result_absent"),
        executed_control("cross_tenant_history_isolation", "correct_history_read", "wrong_tenant_history_empty"),
        executed_control(
            "wrong_scope_claim_denial",
            "wrong_tenant_claim_operation_denied",
            "wrong_environment_claim_operation_denied",
            "wrong_scope_claim_did_not_mutate_state",
            "correct_scope_claim_operation_succeeded",
        ),
        executed_control("wrong_scope_search_isolation", "correct_scope_search", "wrong_scope_search_empty"),
    ]
    completed = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "commit_sha": _sha(),
        "elasticsearch_version": security_client.info()["version"]["number"],
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "scenario_count": len(controls),
        "passed_count": sum(c.passed for c in controls),
        "failed_count": 0,
        "controls": [c.__dict__ for c in controls],
        "test_names": sorted({c.test_node_id for c in controls}),
        "redacted_references": [],
        "result": "passed",
    }
    security_evidence_dir.mkdir(parents=True, exist_ok=True)
    (security_evidence_dir / "security-report.json").write_text(json.dumps(report, indent=2) + "\n")
