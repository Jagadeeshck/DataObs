import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_local_evidence_cannot_apply_hosted_promotion(tmp_path):
    source = json.loads((ROOT / "certification/evidence/certification-evidence.json").read_text())
    source["capabilities"]["platform.migrations"] = {
        "status": "passed",
        "tests": ["migration-clean-install", "migration-upgrade"],
        "artifacts": [],
        "limitations": [],
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(source))
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_certification_evidence.py"),
            str(path),
            "--apply",
            "--output",
            str(tmp_path / "report.md"),
        ],
        cwd=ROOT,
    )
    assert result.returncode == 1
