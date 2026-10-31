import json
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.certification.provenance import certification_commit_sha
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
    assert inventory["gate_0_state"] == "GATE_0_BLOCKED"
    assert len(inventory["audited_main_sha"]) == 40
    assert inventory["observed_workflow_sha"] == inventory["audited_main_sha"]
    assert inventory["candidate_sha"] is None
    for item in inventory["blockers"]:
        assert item["owner"] and item["workflow"] and item["root_cause"] and item["resolution"]
        assert item["source_sha"] == inventory["observed_workflow_sha"]
        assert item["hosted_state"] in {"passed", "failed", "blocked", "not_run"}
        assert item["final_head_hosted_state"] == "not_run"
        assert item["workflow_run_id"]
        if item.get("artifact_id") is None:
            assert item["hosted_state"] == "failed"
            assert item.get("artifact_state") == "missing"
        else:
            assert item["artifact_id"]
            assert item.get("artifact_state") == "retained"
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
    assert (
        "DATAOBS_KIND_DIAGNOSTICS: gate0-packaging-evidence/kind-diagnostics.txt"
        in workflows["beta-deployment-packaging.yml"]
    )
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
    junit.write_text(
        "<testsuite tests='1' failures='0'>"
        "<testcase name='test_beta_backup_restore_exact_state_and_tenant_isolation'/>"
        "</testsuite>"
    )
    good = {
        "commit_sha": certification_commit_sha(),
        "snapshot_repository": "synthetic-ci",
        "snapshot": "bounded-test",
        "snapshot_result": "pass",
        "destructive_deletion_result": "pass",
        "restore_result": "pass",
        "integrity_verification": "pass",
        "recovery_result": "pass",
        "started_at": "2026-10-28T00:00:00+00:00",
        "completed_at": "2026-10-28T00:01:00+00:00",
        "backup_duration_seconds": 1.0,
        "restore_duration_seconds": 2.0,
        "duration_seconds": 60.0,
        "status": "pass",
        "elasticsearch_version": "9.5.5",
        "terminal_migration": "0033_team1_stream_schema_intelligence_runtime",
        "tenant_isolation": "pass",
        "redaction_status": "pass",
        "resources": {"dataobs-incidents-v1": {"count": 2, "sha256": "a" * 64}},
    }
    report.write_text(json.dumps(good))
    validate(report, junit)

    for key, value in [
        ("commit_sha", "0" * 40),
        ("elasticsearch_version", "9.0.0"),
        ("restore_result", "fail"),
        ("integrity_verification", None),
        ("restore_duration_seconds", None),
        ("backup_duration_seconds", -1),
    ]:
        report.write_text(json.dumps(good | {key: value}))
        with pytest.raises((ValueError, TypeError)):
            validate(report, junit)
    report.write_text(json.dumps(good))
    for xml in [
        "<broken",
        "<testsuite tests='0'/>",
        (
            "<testsuite>"
            "<testcase name='test_beta_backup_restore_exact_state_and_tenant_isolation'><skipped/></testcase>"
            "</testsuite>"
        ),
    ]:
        junit.write_text(xml)
        with pytest.raises(Exception):
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


def test_gate_0_manifest_requires_supply_chain_and_browser_accessibility():
    manifest = yaml.safe_load((ROOT / "docs/release/v0.2.0-gate-0-certification-manifest.yaml").read_text())
    capabilities = {item["capability_id"]: item for item in manifest["capabilities"]}

    shared = capabilities["shared-ci"]
    assert "Production image security and SBOM" in shared["required_jobs"]

    console = capabilities["console-browser-accessibility"]
    assert console["workflow"] == "console-beta-closure.yml"
    assert console["artifact"] == "console-beta-closure-v1-evidence"
    assert console["required_jobs"] == ["validate", "verify-evidence"]
    assert console["required_test_categories"] == ["browser", "accessibility"]

    workflow = (ROOT / ".github/workflows/console-beta-closure.yml").read_text()
    assert "write_evidence_envelope.py --output evidence/evidence.json" in workflow
    assert "--test-category browser --test-category accessibility" in workflow
    assert "check_downloaded_envelope.py --directory evidence" in workflow


def test_api_template_has_unique_security_environment_entries():
    template = (ROOT / "helm/dataobs/templates/api.yaml").read_text()
    for name in (
        "DATAOBS_AUTHORIZATION_SOURCE",
        "DATAOBS_SECURITY_BOOTSTRAP_ENABLED",
        "DATAOBS_OIDC_MAXIMUM_TOKEN_LIFETIME_SECONDS",
        "DATAOBS_OIDC_ALLOWED_AUTHORISED_PARTIES",
        "DATAOBS_OIDC_ALLOWED_TOKEN_TYPES",
        "DATAOBS_OIDC_REQUIRE_JTI_FOR_SERVICE_TOKENS",
        "DATAOBS_CORS_ALLOWED_ORIGINS",
    ):
        assert template.count(f"name: {name}") == 1


def test_kind_smoke_failure_diagnostics_include_events_and_container_logs():
    script = (ROOT / "scripts/deployment/kind_smoke_test.sh").read_text()
    assert 'kubectl -n "$NS" get events --sort-by=.lastTimestamp' in script
    assert 'kubectl -n "$NS" logs "$pod" --tail=300' in script
    assert 'kubectl -n "$NS" logs "$pod" --previous --tail=300' in script


def test_packaged_runtimes_do_not_depend_on_release_script_modules():
    for relative in (
        "src/api/platform_lifecycle_routes.py",
        "src/platform_operations/supportability.py",
    ):
        source = (ROOT / relative).read_text()
        assert "from scripts." not in source
        assert "import scripts." not in source


def test_certification_migrations_default_to_published_elasticsearch_endpoint():
    script = (ROOT / "scripts/certification/apply_migrations.sh").read_text()
    assert 'ELASTICSEARCH_URL:-http://127.0.0.1:19200' in script
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "./scripts/certification/apply_migrations.sh" in workflow
    assert "./scripts/certification/apply_migrations.sh\n          ./bin/dataobs elastic status" not in workflow


def test_kafka_observer_image_contains_runtime_telemetry_dependency():
    dockerfile = (ROOT / "Dockerfile.kafka-observer").read_text()
    cli = (ROOT / "services/kafka_observer/cli.py").read_text()
    assert "from src.telemetry import init_telemetry" in cli
    assert "COPY src src" in dockerfile
