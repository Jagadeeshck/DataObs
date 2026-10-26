import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.security.build_security_evidence import REQUIRED_REPORTS, build
from scripts.security.create_security_release_gate import create
from scripts.security.verify_security_evidence import verify

SHA_A = "a" * 40
SHA_B = "b" * 40


def runtime_reports(path: Path, sha: str = SHA_A) -> None:
    path.mkdir()
    for name in REQUIRED_REPORTS:
        body = {"repository": "Jagadeeshck/DataObs", "sha": sha, "status": "pass"}
        if name == "security-posture-report.json":
            body["overall_state"] = "INCOMPLETE"
        if name == "security-release-gate.json":
            body["state"] = "INCOMPLETE"
        (path / name).write_text(json.dumps(body))


def provenance() -> dict[str, str]:
    return {"workflow": "test.yml", "workflow_run_id": "1", "run_attempt": "1", "event": "test"}


def test_builder_requires_explicit_current_run_reports(tmp_path, monkeypatch):
    source = tmp_path / "runtime"
    runtime_reports(source)
    (source / REQUIRED_REPORTS[0]).unlink()
    # A root-style historical copy must never be considered.
    (tmp_path / REQUIRED_REPORTS[0]).write_text(json.dumps({"sha": SHA_A}))
    monkeypatch.chdir(Path(__file__).parents[2])
    with pytest.raises(FileNotFoundError, match=REQUIRED_REPORTS[0]):
        build(source, tmp_path / "bundle", SHA_A, provenance())


def test_verifier_rejects_mixed_sha_and_checksum_tampering(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[2])
    source = tmp_path / "runtime"
    runtime_reports(source)
    bundle = tmp_path / "bundle"
    build(source, bundle, SHA_A, provenance())
    verify(bundle, SHA_A, "Jagadeeshck/DataObs")

    report = bundle / "route-security-report.json"
    report.write_text(json.dumps({"sha": SHA_B}))
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify(bundle, SHA_A, "Jagadeeshck/DataObs")

    manifest = json.loads((bundle / "manifest.json").read_text())
    for item in manifest["files"]:
        if item["path"] == report.name:
            item["sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="mixed producer SHA"):
        verify(bundle, SHA_A, "Jagadeeshck/DataObs")


@pytest.mark.parametrize(
    "state,allowed", [("PASS", True), ("INCOMPLETE", False), ("UNVALIDATED", False), ("FAIL", False)]
)
def test_release_gate_is_fail_closed_but_reporting_can_complete(tmp_path, state, allowed):
    posture = tmp_path / "posture.json"
    posture.write_text(json.dumps({"repository": "Jagadeeshck/DataObs", "sha": SHA_A, "overall_state": state}))
    gate = create(posture, tmp_path / "gate.json", "local")
    assert gate["release_authorized"] is allowed
    command = [
        sys.executable,
        "scripts/security/create_security_release_gate.py",
        "--posture",
        str(posture),
        "--output",
        str(tmp_path / "enforced.json"),
        "--enforce",
    ]
    result = subprocess.run(command, cwd=Path(__file__).parents[2], check=False)
    assert (result.returncode == 0) is allowed


def test_workflow_uses_downloaded_artifacts_for_each_boundary():
    workflow = yaml.safe_load(
        (Path(__file__).parents[2] / ".github/workflows/team-0-security-compliance-evidence-v1.yml").read_text()
    )
    jobs = workflow["jobs"]
    assert any(step.get("uses") == "actions/upload-artifact@v4" for step in jobs["validation"]["steps"])
    assert any(step.get("uses") == "actions/download-artifact@v4" for step in jobs["posture"]["steps"])
    assert any(step.get("uses") == "actions/download-artifact@v4" for step in jobs["evidence"]["steps"])
    assert any(step.get("uses") == "actions/download-artifact@v4" for step in jobs["verify"]["steps"])
    verify_run = "\n".join(str(step.get("run", "")) for step in jobs["verify"]["steps"])
    assert "downloaded-evidence" in verify_run


def test_beta_tenant_isolation_attestation_has_an_executed_adversarial_suite():
    root = Path(__file__).parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/beta-security-hardening.yml").read_text())
    commands = "\n".join(str(step.get("run", "")) for step in workflow["jobs"]["security"]["steps"])
    assert "--test-category tenant-isolation" in commands
    assert "pytest tests/security tests/certification" in commands
    suite = (root / "tests/security/test_oidc_rbac_tenant.py").read_text()
    assert "tenant-b" in suite and "fails_closed" in suite
