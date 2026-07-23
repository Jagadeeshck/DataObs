import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema

from packages.elastic_store.manifest import DATA_PRODUCT_RECONCILIATION_EVIDENCE

ROOT = Path(__file__).resolve().parents[2]


def test_local_evidence_matches_schema_and_is_not_hosted():
    schema = json.loads((ROOT / "certification/evidence-manifest.schema.json").read_text())
    evidence = json.loads((ROOT / "certification/evidence/certification-evidence.json").read_text())
    jsonschema.validate(evidence, schema)
    assert evidence["workflow_run_id"] is None


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
                        "controls": ["tenant isolation"],
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
    (nested / "manifest.json").write_text("nested manifest payload\n")
    (nested / "certification-evidence.json").write_text("nested evidence payload\n")
    artifacts = []
    import hashlib

    for path in nested.iterdir():
        artifacts.append(
            {"path": path.relative_to(tmp_path).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    encoded = json.dumps({"artifacts": artifacts})
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
