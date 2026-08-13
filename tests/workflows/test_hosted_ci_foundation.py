from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow_texts():
    for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
        yield path, path.read_text()


def test_workflow_yaml_parses_and_requirements_files_exist():
    for path, text in workflow_texts():
        assert yaml.safe_load(text), path
        for line in text.splitlines():
            if "pip install" not in line:
                continue
            for requirement in re.findall(r"-r\s+([^\s'\"]+)", line):
                assert (ROOT / requirement).is_file(), f"{path} references missing {requirement}"


def test_shared_and_azure_bootstrap_precedes_pytest():
    for name in ("reusable-backend-validation.yml", "azure-data-platform-collector-v1.yml"):
        text = (WORKFLOWS / name).read_text()
        bootstrap = text.index("requirements-ci.txt")
        assert bootstrap < text.index("pytest", bootstrap)
        assert "requirements-dev.txt" not in text
    azure = (WORKFLOWS / "azure-data-platform-collector-v1.yml").read_text()
    assert "fetch-depth: 0" in azure
    assert "python -m pytest" in azure


def test_console_uses_pinned_toolchain_and_generated_diff_gate():
    workflow = (WORKFLOWS / "reusable-console-validation.yml").read_text()
    package = (ROOT / "ui/dataobs-console/package.json").read_text()
    assert "node-version: '22'" in workflow
    assert "version: 10.28.1" in workflow
    assert '"packageManager": "pnpm@10.28.1"' in package
    assert "pnpm install --frozen-lockfile" in workflow
    assert workflow.index("pnpm api:generate") < workflow.index("pnpm build")
    assert "git diff --exit-code src/api/generated/schema.ts" in workflow


def test_elasticsearch_readiness_is_before_work_in_repaired_foundations():
    for name in ("reusable-backend-validation.yml", "beta-security-hardening.yml", "beta-backup-restore.yml"):
        text = (WORKFLOWS / name).read_text()
        ready = text.index("wait_for_elasticsearch.py")
        following_work = [
            text.find(token, ready + 1) for token in ("pytest", "Apply existing migrations", "Real Elasticsearch")
        ]
        assert any(position > ready for position in following_work), name


def test_elasticsearch_readiness_timeout_fails_closed():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/wait_for_elasticsearch.py",
            "--url",
            "http://127.0.0.1:1",
            "--timeout",
            "0.05",
            "--interval",
            "0.01",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "timed out" in result.stderr
