import json
import subprocess
import sys
from pathlib import Path

from scripts.certification.ci_summary_manifest import build, verify


def _junit(path: Path) -> None:
    path.write_text("<testsuite tests='1' failures='0' errors='0' skipped='0'><testcase name='ok'/></testsuite>")


def test_ci_summary_script_is_directly_executable():
    subprocess.run(
        [sys.executable, "scripts/certification/ci_summary_manifest.py", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_generic_ci_summary_is_exact_sha_and_digest_bound(tmp_path: Path, monkeypatch):
    sha = "a" * 40
    monkeypatch.setenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs")
    for name in ("contracts", "kafka"):
        directory = tmp_path / name
        directory.mkdir()
        _junit(directory / "results.xml")
    results = {
        "scope": "kafka",
        "partial": True,
        "required_jobs": ["contracts", "kafka"],
        "expected_skipped_jobs": [
            "browser",
            "migrations-incidents",
            "openlineage-product",
            "postgres",
            "security",
        ],
        "errors": [],
    }
    (tmp_path / "job-results.json").write_text(json.dumps(results))
    extra = tmp_path / "production-image-sboms"
    extra.mkdir()
    (extra / "sbom-index.json").write_text('{"status":"pass"}')

    manifest = build(tmp_path, "kafka", sha)

    assert manifest["target_sha"] == sha
    assert manifest["status"] == "pass"
    assert set(manifest["required_jobs"]) == {"contracts", "kafka"}
    assert any(item["path"] == "production-image-sboms/sbom-index.json" for item in manifest["artifact_inventory"])
    assert verify(tmp_path, sha) == []

    (tmp_path / "kafka" / "results.xml").write_text(
        "<testsuite tests='1' failures='1' errors='0' skipped='0'><testcase name='bad'/></testsuite>"
    )
    assert verify(tmp_path, sha)


def test_platform_images_and_kafka_bootstrap_preserve_runtime_dependencies():
    api = Path("Dockerfile.api").read_text()
    compose = Path("docker-compose.certification.yml").read_text()
    observer_wait = Path("scripts/certification/wait_for_kafka_observer.sh").read_text()
    workflow = Path(".github/workflows/ci.yml").read_text()

    assert "COPY integrations ./integrations" in api
    assert "profiles: [kafka-observer]" in compose
    assert "up -d --build kafka-observer" in observer_wait
    assert workflow.index("./scripts/certification/apply_migrations.sh") < workflow.index(
        "./scripts/certification/wait_for_kafka_observer.sh"
    )
    assert "ci_summary_manifest.py build" in workflow
    assert "build_manifest.py artifacts" not in workflow
