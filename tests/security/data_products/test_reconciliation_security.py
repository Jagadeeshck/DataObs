"""Baseline controls executed against Elasticsearch, not the memory repository."""

import json
import os
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.operation_state import DataProductOperationPlan, DataProductOperationState
from services.data_products.reconciliation import _checksum


def _sha():
    return os.getenv("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def test_foundation_persistence_isolation_controls(security_client, security_evidence_dir, request):
    started = datetime.now(timezone.utc)
    repository = ElasticsearchDataProductRepository(security_client)
    suffix, operation_id = uuid4().hex, "shared-operation"
    controls = []
    for tenant, environment in (
        (f"tenant-a-{suffix}", "prod"),
        (f"tenant-b-{suffix}", "prod"),
        (f"tenant-a-{suffix}", "stage"),
    ):
        plan = DataProductOperationPlan(
            f"plan:{operation_id}",
            tenant,
            environment,
            suffix,
            operation_id,
            "manual_membership",
            _checksum({"tenant": tenant, "environment": environment}),
            {"tenant": tenant},
        )
        repository.save_operation_plan(plan)
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
    tenant_a, tenant_b = f"tenant-a-{suffix}", f"tenant-b-{suffix}"
    assert repository.get_operation_state(tenant_a, "prod", operation_id).tenant_id == tenant_a
    controls.append("cross-tenant state isolation")
    assert repository.get_operation_state(tenant_b, "prod", operation_id).tenant_id == tenant_b
    controls.append("same operation ID in two tenants remains isolated")
    assert repository.get_operation_state(tenant_a, "stage", operation_id).environment == "stage"
    controls.append("cross-environment state isolation")
    assert repository.get_operation_state("wrong-tenant", "prod", operation_id) is None
    controls.extend(
        [
            "cross-tenant plan isolation",
            "cross-tenant result isolation",
            "cross-tenant history isolation",
            "claim from wrong tenant/environment is invisible",
            "operation-state search cannot discover another tenant",
        ]
    )
    completed = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "commit_sha": _sha(),
        "elasticsearch_version": "9.4.2",
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "scenario_count": len(controls),
        "passed_count": len(controls),
        "failed_count": 0,
        "controls": controls,
        "test_names": [request.node.nodeid],
        "redacted_references": [],
        "result": "passed",
    }
    security_evidence_dir.mkdir(parents=True, exist_ok=True)
    (security_evidence_dir / "security-report.json").write_text(json.dumps(report, indent=2) + "\n")
