from __future__ import annotations

import re
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
MIGRATION_BASE = "$(python scripts/resolve_ci_base.py)"


def workflow_texts():
    for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
        yield path, path.read_text()


def workflow_jobs(path: Path):
    return yaml.safe_load(path.read_text())["jobs"].items()


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
    assert "pnpm exec vitest run --reporter=junit --outputFile=../../evidence/console-junit.xml" in workflow
    assert workflow.index("test -s ../../evidence/console-junit.xml") < workflow.index("write_evidence_envelope.py")


def test_elasticsearch_client_pin_is_published_and_checked_for_resolution():
    requirement = "elasticsearch[async]==9.4.1"
    assert requirement in (ROOT / "requirements.txt").read_text()
    assert requirement in (ROOT / "requirements-poc.txt").read_text()
    backend = (WORKFLOWS / "reusable-backend-validation.yml").read_text()
    assert f"pip download --no-deps --dest /tmp/dataobs-elasticsearch-client '{requirement}'" in backend
    assert ">=9.4.2" not in (ROOT / "requirements.txt").read_text()
    assert ">=9.4.2" not in (ROOT / "requirements-poc.txt").read_text()


def test_elasticsearch_readiness_is_before_work_in_repaired_foundations():
    for name in ("reusable-backend-validation.yml", "beta-security-hardening.yml", "beta-backup-restore.yml"):
        text = (WORKFLOWS / name).read_text()
        readiness = (
            "start_gate0_elasticsearch.sh" if name == "beta-security-hardening.yml" else "wait_for_elasticsearch.py"
        )
        ready = text.index(readiness)
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


def test_project_tests_do_not_install_only_ci_dependencies():
    """CI tooling alone must never be mistaken for the product test environment."""
    for path, _ in workflow_texts():
        for job_name, job in workflow_jobs(path):
            commands = "\n".join(str(step.get("run", "")) for step in job.get("steps", []))
            if "pytest" not in commands or "requirements-ci.txt" not in commands:
                continue
            assert "requirements.txt" in commands, f"{path}:{job_name} installs CI-only dependencies before pytest"


def test_migration_history_jobs_use_full_checkout_history():
    for path, _ in workflow_texts():
        for job_name, job in workflow_jobs(path):
            steps = job.get("steps", [])
            if not any("check_migration_immutability.py" in str(step.get("run", "")) for step in steps):
                continue
            checkouts = [step for step in steps if str(step.get("uses", "")).startswith("actions/checkout@")]
            assert checkouts, f"{path}:{job_name} has no checkout"
            assert all(
                str(step.get("with", {}).get("fetch-depth")) == "0" for step in checkouts
            ), f"{path}:{job_name} must fetch complete history for migration immutability"


def test_iam_and_cluster_360_shared_root_cause_regressions():
    iam = (WORKFLOWS / "iam-security.yml").read_text()
    rabbit = (WORKFLOWS / "team-4-rabbitmq-messaging-collector-v1.yml").read_text()
    cluster = (WORKFLOWS / "cluster-360-console.yml").read_text()
    assert (
        "fetch-depth: 0" in iam
        and 'check_migration_immutability.py --base-ref "$(python scripts/resolve_ci_base.py)"' in iam
    )
    assert "requirements.txt -r requirements-ci.txt" in rabbit
    assert cluster.index("wait_for_elasticsearch.py") < cluster.index("packages.elastic_store.cli apply")


def test_migration_checks_use_canonical_base_resolution_or_candidate_input():
    allowed_candidate_workflows = {
        "beta-1-release-candidate.yml",
        "team-0-first-supported-platform-release-v1.yml",
        "team-0-release-candidate.yml",
    }
    for path, text in workflow_texts():
        if "check_migration_immutability.py" not in text or path.name in allowed_candidate_workflows:
            continue
        for line in text.splitlines():
            if "check_migration_immutability.py" in line:
                assert "scripts/resolve_ci_base.py" in line, f"{path} bypasses canonical base resolution"


def _assert_migration_command_has_no_replacement_leftovers(line: str) -> None:
    assert "}}" not in line
    assert "github.event." not in line
    assert "github.base_ref" not in line
    suffix = line.partition(MIGRATION_BASE)[2]
    assert suffix, "canonical resolver command substitution is missing"
    suffix = suffix.lstrip('"').strip()
    assert not suffix or suffix.startswith(("&&", "|")), f"unexpected tokens after base resolver: {suffix}"


def test_migration_commands_have_no_malformed_replacement_leftovers():
    for path, text in workflow_texts():
        for line in text.splitlines():
            if "check_migration_immutability.py" in line and MIGRATION_BASE in line:
                _assert_migration_command_has_no_replacement_leftovers(line)


def test_migration_command_guard_rejects_known_malformed_replacements():
    prefix = f'python scripts/check_migration_immutability.py --base-ref "{MIGRATION_BASE}"'
    malformed = (
        f"{prefix} }}",
        f"{prefix} github.event.pull_request.base.sha",
        f"{prefix} github.base_ref",
        f"{prefix} unexpected-token",
    )
    for line in malformed:
        try:
            _assert_migration_command_has_no_replacement_leftovers(line)
        except AssertionError:
            continue
        raise AssertionError(f"guard accepted malformed migration command: {line}")


def test_elasticsearch_jobs_wait_before_application_interaction_without_sleeps():
    for path, _ in workflow_texts():
        for job_name, job in workflow_jobs(path):
            service = job.get("services", {}).get("elasticsearch", {})
            if "elasticsearch:9.4.2" not in str(service.get("image", "")):
                continue
            commands = [str(step.get("run", "")) for step in job.get("steps", [])]
            interactions = [
                index
                for index, command in enumerate(commands)
                if ("pytest" in command and "pip install" not in command)
                or "check_migration_immutability.py" in command
                or "elastic_store.cli" in command
            ]
            if not interactions:
                continue
            readiness = [index for index, command in enumerate(commands) if "wait_for_elasticsearch.py" in command]
            assert readiness and readiness[0] < interactions[0], f"{path}:{job_name} interacts with ES before readiness"
            assert not any(re.search(r"(?:^|\s)sleep\s+(?:10|30)(?:\s|$)", command) for command in commands)


def test_console_lockfile_has_only_patched_js_yaml_and_keeps_high_audit_gate():
    package = yaml.safe_load((ROOT / "ui/dataobs-console/package.json").read_text())
    lock = (ROOT / "ui/dataobs-console/pnpm-lock.yaml").read_text()
    assert package["pnpm"]["overrides"]["@redocly/openapi-core>js-yaml"] == "4.3.2"
    assert package["pnpm"]["overrides"]["browserslist"] == "4.28.7"
    assert package["pnpm"]["overrides"]["zod"] == ">=4.6.6"
    versions = {tuple(map(int, match)) for match in re.findall(r"js-yaml@(\d+)\.(\d+)\.(\d+)", lock)}
    assert versions and all(version >= (4, 1, 1) for version in versions)
    console_workflow = (WORKFLOWS / "reusable-console-validation.yml").read_text()
    assert "pnpm audit --audit-level high" in console_workflow
    assert "continue-on-error" not in console_workflow


def test_shared_audit_and_helm_commands_are_reproducible():
    ci_requirements = (ROOT / "requirements-ci.txt").read_text()
    assert "black==26.10.1" in ci_requirements
    rabbitmq = (WORKFLOWS / "team-4-rabbitmq-messaging-collector-v1.yml").read_text()
    assert "pip-audit -r requirements.txt -r requirements-ci.txt" in rabbitmq
    for path, text in workflow_texts():
        for line in text.splitlines():
            if "helm lint helm/dataobs" in line:
                assert "--kube-version 1.30.0" in line, f"{path} lints against Helm's changing default"


def test_elasticsearch_readiness_retries_transient_disconnect_and_checks_indices():
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib handler API
            requests.append(self.path)
            if len(requests) == 1:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            body = b"[]" if self.path.startswith("/_cat/indices") else b'{"status":"yellow","timed_out":false}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/wait_for_elasticsearch.py",
                "--url",
                f"http://127.0.0.1:{server.server_port}",
                "--timeout",
                "2",
                "--interval",
                "0.01",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    finally:
        server.shutdown()
        server.server_close()
    assert result.returncode == 0, result.stderr
    assert any(path.startswith("/_cat/indices") for path in requests)
