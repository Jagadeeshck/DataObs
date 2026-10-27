"""Regression coverage for the release metadata dependency boundary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_release_metadata_does_not_import_elasticsearch_client() -> None:
    script = """
import builtins
import sys

sys.path.insert(0, {root!r})

real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "elasticsearch" or name.startswith("elasticsearch."):
        raise AssertionError("release metadata imported the Elasticsearch runtime client")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from scripts.release.release_metadata import ELASTICSEARCH_VERSION, terminal_migration

assert ELASTICSEARCH_VERSION == "9.4.2"
assert terminal_migration() == "0033_team1_stream_schema_intelligence_runtime"
""".format(root=str(ROOT))
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_console_evidence_writer_help_uses_minimal_python_dependencies() -> None:
    script = """
import builtins
import runpy
import sys

real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "elasticsearch" or name.startswith("elasticsearch."):
        raise AssertionError("evidence writer imported the Elasticsearch runtime client")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
sys.argv = ["write_evidence_envelope.py", "--help"]
runpy.run_path("scripts/certification/write_evidence_envelope.py", run_name="__main__")
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--output" in result.stdout


def test_migration_plan_cli_does_not_import_elasticsearch_client() -> None:
    script = """
import builtins
import runpy
import sys

real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "elasticsearch" or name.startswith("elasticsearch."):
        raise AssertionError("migration plan imported the Elasticsearch runtime client")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
sys.argv = ["packages.elastic_store.cli", "plan"]
runpy.run_module("packages.elastic_store.cli", run_name="__main__")
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '"migration_id": "0033_team1_stream_schema_intelligence_runtime"' in result.stdout


def test_backup_restore_validator_is_directly_executable() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/certification/validate_backup_restore_evidence.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--report" in result.stdout
