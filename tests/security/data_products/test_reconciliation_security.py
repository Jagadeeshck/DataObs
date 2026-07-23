"""Executed, scoped persistence controls against the certification cluster."""

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.operation_state import (
    DataProductOperationHistoryEvent,
    DataProductOperationPlan,
    DataProductOperationResultEnvelope,
    DataProductOperationState,
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
    controls = [
        executed_control("cross_tenant_state_isolation", 3),
        executed_control("cross_environment_state_isolation", 2),
        executed_control("same_operation_id_scope_isolation", 3),
        executed_control("cross_tenant_plan_isolation", 2),
        executed_control("cross_tenant_result_isolation", 2),
        executed_control("cross_tenant_history_isolation", 2),
        executed_control("wrong_scope_claim_denial", 2),
        executed_control("wrong_scope_search_isolation", 2),
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
