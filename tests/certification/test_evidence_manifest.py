import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


def test_local_evidence_matches_schema_and_is_not_hosted():
    schema = json.loads((ROOT / "certification/evidence-manifest.schema.json").read_text())
    evidence = json.loads((ROOT / "certification/evidence/certification-evidence.json").read_text())
    jsonschema.validate(evidence, schema)
    assert evidence["workflow_run_id"] is None


def test_verifier_rejects_artifact_mutated_after_manifest(tmp_path):
    artifact = tmp_path / "backend" / "result.txt"
    artifact.parent.mkdir()
    artifact.write_text("passed\n")
    subprocess.run([sys.executable, str(ROOT / "scripts/certification/build_manifest.py"), str(tmp_path)], check=True)
    artifact.write_text("tampered\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/certification/verify_artifacts.py"), str(tmp_path)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "sha256 mismatch: backend/result.txt" in result.stdout
