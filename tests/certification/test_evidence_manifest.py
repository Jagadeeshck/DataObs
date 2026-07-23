import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from packages.elastic_store.manifest import DATA_PRODUCT_RECONCILIATION_EVIDENCE
from scripts.certification.build_manifest import _foundation_provenance, _junit_summary
from scripts.certification.verify_artifacts import _manifest_provenance_errors

ROOT = Path(__file__).resolve().parents[2]


def _hosted_manifest(**overrides):
    manifest = {
        "schema_version": "1.0",
        "certification_profile": "data-product-runtime-foundation",
        "workflow_event": "pull_request",
        "full_reconciliation_certified": False,
        "release_readiness": "blocked",
        "capabilities": {},
        "repository": "Jagadeeshck/DataObs",
        "commit_sha": "a" * 40,
        "workflow_run_id": 123,
        "workflow_run_url": "https://github.com/Jagadeeshck/DataObs/actions/runs/123",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:00:01Z",
        "artifacts": [],
    }
    manifest.update(overrides)
    return manifest


def _write_junit(path, *, tests=1, failures=0, errors=0, reasons=()):
    cases = "".join(
        f'<testcase name="skip-{number}"><skipped message="{reason}"/></testcase>'
        for number, reason in enumerate(reasons)
    )
    path.write_text(
        f'<testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{len(reasons)}">'
        f"{cases}</testsuite>"
    )


def test_unit_junit_approved_skips_are_accounted(tmp_path):
    path = tmp_path / "unit.xml"
    reason = "hosted runtime secret only"
    _write_junit(path, tests=2, reasons=(reason,))
    summary = _junit_summary(path)
    assert summary["skipped"] == 1
    assert summary["skip_reasons"] == [reason]
    assert summary["policy"]["allow_skips"] is True


@pytest.mark.parametrize("name", ["contracts.xml", "migrations.xml", "elasticsearch.xml", "security.xml"])
def test_required_junit_rejects_skips(tmp_path, name):
    path = tmp_path / name
    _write_junit(path, reasons=("hosted runtime secret only",))
    with pytest.raises(ValueError, match="forbids skips"):
        _junit_summary(path)


def test_unit_junit_rejects_unknown_skip_failures_and_zero_tests(tmp_path):
    path = tmp_path / "unit.xml"
    _write_junit(path, reasons=("new unexpected skip",))
    with pytest.raises(ValueError, match="unapproved"):
        _junit_summary(path)
    _write_junit(path, failures=1)
    with pytest.raises(ValueError, match="failures/errors"):
        _junit_summary(path)
    _write_junit(path, tests=0)
    with pytest.raises(ValueError, match="empty"):
        _junit_summary(path)


def test_local_evidence_matches_schema_and_is_not_hosted():
    schema = json.loads((ROOT / "certification/evidence-manifest.schema.json").read_text())
    evidence = json.loads((ROOT / "certification/evidence/certification-evidence.json").read_text())
    jsonschema.validate(evidence, schema)
    assert evidence["workflow_run_id"] is None


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"workflow_event": "workflow_dispatch"}, "workflow event"),
        ({"workflow_event": None}, "workflow event"),
        ({"started_at": ""}, "started_at"),
        ({"started_at": "2026-01-01T00:00:00"}, "started_at"),
        ({"workflow_run_id": None}, "run ID"),
        ({"workflow_run_id": 0}, "run ID"),
        ({"workflow_run_id": "123"}, "run ID"),
        ({"workflow_run_url": None}, "run URL"),
    ],
)
def test_verifier_rejects_invalid_hosted_provenance(override, message):
    assert any(message in error for error in _manifest_provenance_errors(_hosted_manifest(**override)))


def test_manifest_builder_requires_explicit_pull_request_provenance(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("DATA_PRODUCT_CERTIFICATION_SHA", "a" * 40)
    monkeypatch.setenv("CERTIFICATION_HEAD_SHA", "a" * 40)
    monkeypatch.setenv("CERTIFICATION_RUN_ID", "123")
    monkeypatch.setenv("CERTIFICATION_RUN_URL", "https://github.com/Jagadeeshck/DataObs/actions/runs/123")
    monkeypatch.setenv("CERTIFICATION_STARTED_AT", "2026-01-01T00:00:00Z")
    monkeypatch.setenv("CERTIFICATION_EVENT_NAME", "workflow_dispatch")
    with pytest.raises(ValueError, match="pull_request"):
        _foundation_provenance(completed_at="2026-01-01T00:00:01Z")
    monkeypatch.setenv("CERTIFICATION_EVENT_NAME", "pull_request")
    provenance = _foundation_provenance(completed_at="2026-01-01T00:00:01Z")
    assert provenance["workflow_run_id"] == 123
    assert provenance["commit_sha"] == "a" * 40


def test_foundation_uses_head_sha_when_github_sha_is_merge_sha(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    monkeypatch.setenv("DATA_PRODUCT_CERTIFICATION_SHA", "a" * 40)
    monkeypatch.setenv("CERTIFICATION_HEAD_SHA", "a" * 40)
    monkeypatch.setenv("CERTIFICATION_EVENT_NAME", "pull_request")
    monkeypatch.setenv("CERTIFICATION_RUN_ID", "123")
    monkeypatch.setenv("CERTIFICATION_RUN_URL", "https://github.com/Jagadeeshck/DataObs/actions/runs/123")
    monkeypatch.setenv("CERTIFICATION_STARTED_AT", "2026-01-01T00:00:00Z")
    assert _foundation_provenance(completed_at="2026-01-01T00:00:01Z")["commit_sha"] == "a" * 40


def test_full_profile_does_not_receive_foundation_provenance_policy():
    manifest = _hosted_manifest(
        certification_profile="data-product-reconciliation-full",
        workflow_event=None,
        workflow_run_id=None,
        workflow_run_url=None,
    )
    errors = _manifest_provenance_errors(manifest)
    assert not any("workflow event" in error or "run ID" in error or "run URL" in error for error in errors)


def test_unknown_profile_fails_closed():
    assert _manifest_provenance_errors(_hosted_manifest(certification_profile="unknown")) == [
        "unknown certification profile"
    ]


def test_verifier_rejects_artifact_mutated_after_manifest(tmp_path):
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    scenario = {
        "schema_version": "1.0",
        "scenario": "certification-test",
        "commit_sha": commit,
        "elasticsearch_version": "9.4.2",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:00:01Z",
        "test_names": ["test_certification"],
        "assertion_summary": ["evidence validated"],
        "redacted_references": [],
        "result": "passed",
    }
    for name in DATA_PRODUCT_RECONCILIATION_EVIDENCE:
        path = tmp_path / name
        if name.endswith(".xml"):
            path.write_text('<testsuite tests="1" failures="0" errors="0"/>\n')
        elif name == "security-report.json":
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "commit_sha": commit,
                        "elasticsearch_version": "9.4.2",
                        "started_at": "2026-01-01T00:00:00Z",
                        "completed_at": "2026-01-01T00:00:01Z",
                        "scenario_count": 1,
                        "passed_count": 1,
                        "failed_count": 0,
                        "controls": [
                            {
                                "control_id": "full_profile_tenant_isolation",
                                "assertion_count": 1,
                                "assertion_evidence": ["tenant isolation"],
                                "passed": True,
                            }
                        ],
                        "test_names": ["test_security"],
                        "redacted_references": ["tenant:sha256:abc"],
                        "result": "passed",
                    }
                )
            )
        elif name == "sentinel-report.json":
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "commit_sha": commit,
                        "elasticsearch_version": "9.4.2",
                        "started_at": "2026-01-01T00:00:00Z",
                        "completed_at": "2026-01-01T00:00:01Z",
                        "files_scanned": 1,
                        "sentinels_injected": 1,
                        "sentinels_redacted": 1,
                        "sentinels_remaining": 0,
                        "test_names": ["test_sentinels"],
                        "result": "passed",
                    }
                )
            )
        elif name.endswith(".json"):
            path.write_text(json.dumps(scenario))
        else:
            path.write_text("redacted certification log\n")
    env = {
        **os.environ,
        "DATA_PRODUCT_CERTIFICATION_PROFILE": "data-product-reconciliation-full",
        "CERTIFICATION_JOB_RESULTS": json.dumps(
            {
                "data-product-reconciliation-contracts": "success",
                "data-product-reconciliation-unit": "success",
                "data-product-reconciliation-elasticsearch": "success",
                "data-product-reconciliation-security": "success",
            }
        ),
    }
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/certification/build_manifest.py"), str(tmp_path)],
        check=True,
        env=env,
    )
    clean = subprocess.run(
        [sys.executable, str(ROOT / "scripts/certification/verify_artifacts.py"), str(tmp_path)],
        text=True,
        capture_output=True,
    )
    assert clean.returncode == 0, clean.stdout
    artifact = tmp_path / "redacted.log"
    artifact.write_text("tampered\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/certification/verify_artifacts.py"), str(tmp_path)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "sha256 mismatch: redacted.log" in result.stdout


def test_verifier_requires_byte_identical_manifest_alias(tmp_path):
    authoritative = tmp_path / "certification-evidence.json"
    authoritative.write_text('{"artifacts": []}\n')
    (tmp_path / "manifest.json").write_text('{"artifacts": ["different"]}\n')
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/certification/verify_artifacts.py"), str(tmp_path)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "not byte-identical" in result.stdout


def test_verifier_rejects_manifest_self_listing(tmp_path):
    payload = {
        "artifacts": [
            {
                "path": "manifest.json",
                "sha256": "0" * 64,
            }
        ]
    }
    encoded = json.dumps(payload)
    (tmp_path / "certification-evidence.json").write_text(encoded)
    (tmp_path / "manifest.json").write_text(encoded)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/certification/verify_artifacts.py"), str(tmp_path)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "manifest must not list itself" in result.stdout


def test_nested_manifest_named_files_are_ordinary_hashed_artifacts(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_payload = json.dumps({"commit_sha": "a" * 40})
    (nested / "manifest.json").write_text(nested_payload)
    (nested / "certification-evidence.json").write_text(nested_payload)
    artifacts = []
    import hashlib

    for path in nested.iterdir():
        artifacts.append(
            {"path": path.relative_to(tmp_path).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    encoded = json.dumps(_hosted_manifest(artifacts=artifacts))
    (tmp_path / "certification-evidence.json").write_text(encoded)
    (tmp_path / "manifest.json").write_text(encoded)
    verify = ROOT / "scripts/certification/verify_artifacts.py"
    assert subprocess.run([sys.executable, str(verify), str(tmp_path)]).returncode == 0
    (nested / "manifest.json").write_text("tampered")
    result = subprocess.run([sys.executable, str(verify), str(tmp_path)], text=True, capture_output=True)
    assert result.returncode == 1
    assert "sha256 mismatch: nested/manifest.json" in result.stdout


def test_verifier_rejects_unexecuted_foundation_security_controls(tmp_path):
    from scripts.certification.verify_artifacts import _security_errors

    (tmp_path / "security-report.json").write_text(
        json.dumps(
            {
                "controls": [{"control_id": "manually_appended", "assertion_count": 0, "passed": True}],
                "scenario_count": 2,
                "passed_count": 2,
                "failed_count": 0,
                "result": "passed",
            }
        )
    )
    errors = _security_errors(tmp_path)
    assert "required foundation security control set is incomplete" in errors
    assert "security control has zero assertions" in errors
    assert "security control count mismatch" in errors


def test_verifier_rejects_wrong_scope_control_without_claim_mutation_evidence(tmp_path):
    from scripts.certification.verify_artifacts import REQUIRED_FOUNDATION_CONTROLS, _security_errors

    controls = [
        {
            "control_id": control_id,
            "assertion_count": 1,
            "assertion_evidence": ["read_only_assertion"],
            "passed": True,
        }
        for control_id in REQUIRED_FOUNDATION_CONTROLS
    ]
    (tmp_path / "security-report.json").write_text(
        json.dumps(
            {
                "controls": controls,
                "scenario_count": len(controls),
                "passed_count": len(controls),
                "failed_count": 0,
                "result": "passed",
            }
        )
    )
    assert "wrong-scope claim control lacks claim-mutation assertion evidence" in _security_errors(tmp_path)
