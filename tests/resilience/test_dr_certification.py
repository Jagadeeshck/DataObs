import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/resilience/verify_dr_certification.py")


def test_validator_fails_closed_without_evidence(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--sha", "a" * 40, "--profile", "hosted"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "missing evidence.json" in result.stdout
    assert "production profile requires retained hosted evidence" in result.stdout


def test_phase_adapter_rejects_unknown_phase():
    result = subprocess.run(
        ["bash", "scripts/resilience/certification_phase.sh", "destroy-everything"], text=True, capture_output=True
    )
    assert result.returncode == 2
    assert "unknown DR certification phase" in result.stderr


def test_safety_guard_rejects_production_target():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/resilience/safety_guard.py",
            "--opt-in",
            "I_UNDERSTAND_DESTRUCTIVE_TEST_ONLY",
            "--environment",
            "test",
            "--synthetic-marker",
            "synthetic-a",
            "--sha",
            "a" * 40,
            "--elasticsearch-url",
            "https://prod.example.test:9200",
            "--allow-elasticsearch-host",
            "prod.example.test",
            "--kube-context",
            "kind-test",
            "--maximum-duration",
            "60",
            "--cleanup-plan",
            "delete-kind",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "unsafe target" in result.stderr
