from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_gate_0_inventory_preserves_release_truth_and_defers_freeze():
    inventory = yaml.safe_load((ROOT / "docs/release/v0.2.0-gate-0-blockers.yaml").read_text())

    assert inventory["release_version"] == "0.2.0"
    assert inventory["release_decision"] == "NO_GO"
    assert inventory["security_state"] == "INCOMPLETE"
    assert inventory["supported_platforms"] == []
    assert inventory["candidate_frozen"] is False
    assert inventory["gate_0_state"] == "pending_hosted_verification"
    assert all(item["owner"] and item["first_meaningful_error"] for item in inventory["blockers"])
    assert all(item["state"] == "fixed_locally_pending_hosted" for item in inventory["blockers"])
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
    assert "test -s evidence/results/backup-restore.xml" in workflows["beta-backup-restore.yml"]
    assert "test -s evidence/results/backup-restore.json" in workflows["beta-backup-restore.yml"]
    for name in (
        "beta-security-hardening.yml",
        "pathway-intelligence-backend.yml",
        "first-mvp-demo-smoke.yml",
        "beta-backup-restore.yml",
    ):
        assert "if: always()" in workflows[name]
