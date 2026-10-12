from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import resolve_ci_base

ROOT = Path(__file__).parents[2]
ZERO_SHA = "0" * 40


def commit(repo: Path, name: str) -> str:
    (repo / name).write_text(name)
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", name], cwd=repo, check=True, capture_output=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


@pytest.fixture()
def history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str, str]:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=tmp_path, check=True)
    root = commit(tmp_path, "root")
    parent = commit(tmp_path, "parent")
    head = commit(tmp_path, "head")

    def local_git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr.strip())
        return result.stdout.strip()

    monkeypatch.setattr(resolve_ci_base, "git", local_git)
    return root, parent, head


def test_pull_request_uses_exact_base_sha(history: tuple[str, str, str]) -> None:
    root, _, _ = history
    assert resolve_ci_base.resolve({"pull_request": {"base": {"sha": root}}}, "pull_request", None, "main") == root


def test_ordinary_and_merge_push_use_event_before(history: tuple[str, str, str]) -> None:
    root, parent, _ = history
    assert resolve_ci_base.resolve({"before": parent}, "push", None, "main") == parent
    assert resolve_ci_base.resolve({"before": root}, "push", None, "main") == root


def test_dispatch_falls_back_to_verified_first_parent(history: tuple[str, str, str]) -> None:
    _, parent, _ = history
    assert resolve_ci_base.resolve({}, "workflow_dispatch", None, "HEAD") == parent


def test_zero_push_falls_back_to_parent_but_bootstrap_is_explicit(history: tuple[str, str, str]) -> None:
    _, parent, head = history
    assert resolve_ci_base.resolve({"before": ZERO_SHA}, "push", None, "main") == parent
    assert resolve_ci_base.resolve({"before": ZERO_SHA}, "push", None, "main", bootstrap=True) == head


@pytest.mark.parametrize("candidate", ["HEAD", "missing-sha"])
def test_invalid_or_head_base_fails_closed(history: tuple[str, str, str], candidate: str) -> None:
    with pytest.raises(ValueError):
        resolve_ci_base.resolve({}, "workflow_dispatch", candidate, "main")


def test_missing_pr_base_fails_closed(history: tuple[str, str, str]) -> None:
    with pytest.raises(ValueError, match="missing"):
        resolve_ci_base.resolve({}, "pull_request", None, "main")


def test_root_commit_requires_bootstrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=tmp_path, check=True)
    root = commit(tmp_path, "root")

    def local_git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr.strip())
        return result.stdout.strip()

    monkeypatch.setattr(resolve_ci_base, "git", local_git)
    with pytest.raises(ValueError, match="root commit"):
        resolve_ci_base.resolve({"before": ZERO_SHA}, "push", None, "main")
    assert resolve_ci_base.resolve({"before": ZERO_SHA}, "push", None, "main", bootstrap=True) == root


def test_unavailable_shallow_base_has_actionable_error(history: tuple[str, str, str]) -> None:
    with pytest.raises(ValueError, match="fetch-depth: 0"):
        resolve_ci_base.resolve({"before": "a" * 40}, "push", None, "main")
