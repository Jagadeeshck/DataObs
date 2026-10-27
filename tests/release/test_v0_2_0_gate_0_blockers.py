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
    assert all(item["owner"] and item["workflow"] and item["hosted_state"] for item in inventory["blockers"])
    assert all(item["first_meaningful_error"] or item["hosted_state"] == "passed" for item in inventory["blockers"])
    assert {item["id"]: item["hosted_state"] for item in inventory["blockers"]} == {
        "T0-RC-HELM-PROFILES": "fixed_locally_pending_rerun",
        "T0-RC-BACKUP-EVIDENCE": "fixed_locally_pending_rerun",
        "T0-RC-SECURITY-SUITES": "domain_failure_requires_triage",
        "T1-RC-PATHWAY-FIXTURES": "domain_failure_requires_triage",
        "T0-RC-MVP-SMOKE": "not_run",
        "T0-RC-FOUNDATION": "passed",
    }
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
    assert "migration-apply.log" in workflows["beta-security-hardening.yml"]
    assert "migration-apply.log" in workflows["pathway-intelligence-backend.yml"]
    assert "first-mvp-demo-diagnostics-${{ github.sha }}" in workflows["first-mvp-demo-smoke.yml"]
    assert "validate_backup_restore_evidence.py" in workflows["beta-backup-restore.yml"]
    assert "envelope-generation.log" in workflows["beta-backup-restore.yml"]
    for name in (
        "beta-security-hardening.yml",
        "pathway-intelligence-backend.yml",
        "first-mvp-demo-smoke.yml",
        "beta-backup-restore.yml",
    ):
        assert "if: always()" in workflows[name]


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
