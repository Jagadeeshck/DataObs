import json
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.certification.validate_backup_restore_evidence import validate
from scripts.deployment.write_structural_digest_values import COMPONENTS, structural_values

ROOT = Path(__file__).resolve().parents[2]


def test_gate_0_inventory_preserves_release_truth_and_defers_freeze():
    inventory = yaml.safe_load((ROOT / "docs/release/v0.2.0-gate-0-blockers.yaml").read_text())

    assert inventory["release_version"] == "0.2.0"
    assert inventory["release_decision"] == "NO_GO"
    assert inventory["security_state"] == "INCOMPLETE"
    assert inventory["supported_platforms"] == []
    assert inventory["candidate_frozen"] is False
    assert inventory["gate_0_state"] == "pending_hosted_verification"
    assert inventory["audited_main_sha"] == "b39a66d1546feba70de84aa6d8c9956e5892d16d"
    assert inventory["observed_workflow_sha"] == inventory["audited_main_sha"]
    assert all(item["owner"] and item["workflow"] and item["hosted_state"] for item in inventory["blockers"])
    assert all(item["first_meaningful_error"] or item["hosted_state"] == "passed" for item in inventory["blockers"])
    assert {item["id"]: item["hosted_state"] for item in inventory["blockers"]} == {
        "T0-RC-HELM-PROFILES": "blocked_external_configuration",
        "T0-RC-BACKUP-EVIDENCE": "requires_authenticated_artifact_triage",
        "T0-RC-SECURITY-SUITES": "shared_migration_failure_requires_triage",
        "T1-RC-PATHWAY-FIXTURES": "blocked_by_team_0_migration",
        "T0-RC-MVP-SMOKE": "not_run",
        "T0-RC-FOUNDATION": "passed",
    }
    assert {item["id"]: item["workflow_run_id"] for item in inventory["blockers"]} == {
        "T0-RC-HELM-PROFILES": 40578796841,
        "T0-RC-BACKUP-EVIDENCE": 40578797192,
        "T0-RC-SECURITY-SUITES": 40578796917,
        "T1-RC-PATHWAY-FIXTURES": 40578796828,
        "T0-RC-MVP-SMOKE": None,
        "T0-RC-FOUNDATION": 40578797145,
    }
    summary = inventory["latest_head_workflow_summary"]
    assert summary["exact_sha"] == inventory["audited_main_sha"]
    assert (summary["observed_total"], summary["passed"], summary["failed"]) == (26, 7, 19)
    assert (
        len(summary["passed_runs"]) + sum(len(runs) for runs in summary["failed_runs_by_owner"].values())
        == summary["observed_total"]
    )
    execution = {item["owner"]: item for item in inventory["team_execution_order"]}
    assert execution["Team 0"]["branch"] == "codex/team0-v0-2-0-shared-stabilization"
    assert all(execution[f"Team {team}"]["branch"].startswith("pending_") for team in range(1, 6))
    assert inventory["gate_0_exit_criteria"]["freeze_after_gate_0_only"] is True


def test_failed_release_infrastructure_retains_diagnostics():
    workflows = {
        name: (ROOT / ".github/workflows" / name).read_text()
        for name in (
            "beta-deployment-packaging.yml",
            "beta-security-hardening.yml",
            "pathway-intelligence-backend.yml",
            "first-mvp-demo-smoke.yml",
            "beta-backup-restore.yml",
        )
    }

    assert "evidence/helm-lint.log" in workflows["beta-deployment-packaging.yml"]
    assert "evidence/migration-base-error.log" in workflows["beta-deployment-packaging.yml"]
    assert "evidence/migration-immutability.log" in workflows["beta-deployment-packaging.yml"]
    assert "DATAOBS_KIND_DIAGNOSTICS: evidence/kind-diagnostics.txt" in workflows["beta-deployment-packaging.yml"]
    assert "migration-apply.log" in workflows["beta-security-hardening.yml"]
    assert "team-0-security-hardening-evidence/security-junit.xml" in workflows["beta-security-hardening.yml"]
    assert "migration-apply.log" in workflows["pathway-intelligence-backend.yml"]
    assert "evidence/pathway-intelligence-junit.xml" in workflows["pathway-intelligence-backend.yml"]
    assert "first-mvp-demo-diagnostics-${{ github.sha }}" in workflows["first-mvp-demo-smoke.yml"]
    assert "validate_backup_restore_evidence.py" in workflows["beta-backup-restore.yml"]
    assert "envelope-generation.log" in workflows["beta-backup-restore.yml"]
    for name in (
        "beta-deployment-packaging.yml",
        "beta-security-hardening.yml",
        "pathway-intelligence-backend.yml",
        "beta-backup-restore.yml",
    ):
        assert "set -o pipefail" in workflows[name]
    for name in (
        "beta-security-hardening.yml",
        "pathway-intelligence-backend.yml",
        "first-mvp-demo-smoke.yml",
        "beta-backup-restore.yml",
    ):
        assert "if: always()" in workflows[name]


def test_mvp_smoke_runs_on_every_main_sha_but_keeps_pr_scope():
    workflow = yaml.safe_load((ROOT / ".github/workflows/first-mvp-demo-smoke.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))

    assert triggers["push"] == {"branches": ["main"]}
    assert "paths" in triggers["pull_request"]


def test_helm_profiles_pin_kubernetes_and_use_re2_compatible_schema():
    workflow = (ROOT / ".github/workflows/beta-deployment-packaging.yml").read_text()
    schema = (ROOT / "helm/dataobs/values.schema.json").read_text()

    template_commands = [line for line in workflow.splitlines() if "helm template dataobs helm/dataobs" in line]
    assert len(template_commands) == 5
    assert all("--kube-version 1.30.0" in line for line in template_commands)
    assert "(?!" not in schema
    values = structural_values()
    assert set(values) == set(COMPONENTS)
    assert all(item["image"]["digest"].startswith("sha256:") for item in values.values())
    assert all(item["image"]["digest"] not in {"sha256:" + digit * 64 for digit in "01f"} for item in values.values())


def test_backup_restore_evidence_validator_is_fail_closed(tmp_path: Path):
    junit = tmp_path / "report.xml"
    report = tmp_path / "report.json"
    junit.write_text("<testsuite tests='1' failures='0'/>")
    good = {
        "status": "pass",
        "elasticsearch_version": "9.4.2",
        "terminal_migration": "0033_team1_stream_schema_intelligence_runtime",
        "tenant_isolation": "pass",
        "redaction_status": "pass",
        "resources": {"dataobs-incidents-v1": {"count": 2, "sha256": "a" * 64}},
    }
    report.write_text(json.dumps(good))
    validate(report, junit)

    report.unlink()
    with pytest.raises(ValueError, match="missing or empty destructive restore report"):
        validate(report, junit)


def test_structural_digest_writer_is_deterministic(tmp_path: Path):
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    command = ["python", "scripts/deployment/write_structural_digest_values.py", "--output"]
    subprocess.run(command + [str(first)], cwd=ROOT, check=True)
    subprocess.run(command + [str(second)], cwd=ROOT, check=True)
    assert first.read_bytes() == second.read_bytes()
