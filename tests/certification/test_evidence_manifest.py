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
                        "scenario_count": 1,
                        "passed_count": 1,
                        "failed_count": 0,
                        "controls": ["tenant isolation"],
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
                        "files_scanned": 1,
                        "sentinels_injected": 1,
                        "sentinels_redacted": 1,
                        "sentinels_remaining": 0,
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
