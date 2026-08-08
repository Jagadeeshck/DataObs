import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/performance/verify_scale_certification.py")


def test_validator_fails_closed_on_empty_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--sha", "a" * 40, "--profile", "production-ha"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "missing evidence.json" in result.stdout


def test_safety_rejects_production():
    result = subprocess.run(
        [
            sys.executable,
            "tests/performance/run_scale_certification.py",
            "--target",
            "https://prod.example.com",
            "--allow-hosts",
            "prod.example.com",
            "--environment",
            "test",
            "--synthetic-marker",
            "synthetic-ci",
            "--sha",
            "a" * 40,
            "--scenario",
            "api-reads",
            "--profile",
            "development",
            "--topology",
            "local",
            "--duration",
            "1",
            "--concurrency",
            "1",
            "--max-concurrency",
            "1",
            "--output",
            "/tmp/never-created",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unsafe target" in result.stderr
