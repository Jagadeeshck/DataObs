import argparse
from pathlib import Path

import yaml

from packages.elastic_store.manifest import migrations
from scripts.certification.write_evidence_envelope import build_envelope
from scripts.check_generated_artifacts import FORBIDDEN_ROOT_REPORTS


def _args(tmp_path: Path, **changes):
    supporting = tmp_path / "results.json"
    supporting.write_text("{}")
    values = dict(
        producer_sha="a" * 40,
        test_category=["typecheck", "build"],
        test_result=["browser=not_run", "accessibility=not_run"],
        supporting_file=[str(supporting)],
        repository="Jagadeeshck/DataObs",
        workflow_file="reusable-console-validation.yml",
        workflow_run_id="1",
        workflow_run_attempt="1",
        event="workflow_dispatch",
        tool_version=[],
        status="pass",
    )
    values.update(changes)
    return argparse.Namespace(**values)


def test_unexecuted_console_categories_are_not_pass(tmp_path):
    summaries = build_envelope(_args(tmp_path))["test_summaries"]
    statuses = {item["category"]: item["status"] for item in summaries}
    assert statuses["browser"] == "not_run"
    assert statuses["accessibility"] == "not_run"


def test_root_migration_report_is_a_forbidden_generated_artifact():
    assert "migration-graph-report.json" in FORBIDDEN_ROOT_REPORTS
    assert not Path("migration-graph-report.json").exists()


def test_migration_compatibility_tracks_registry_and_describes_terminal_semantics():
    contract = yaml.safe_load(Path("config/platform/migration-compatibility.yaml").read_text())
    assert contract["terminal_migration"] == migrations()[-1].migration_id
    assert "schema-intelligence" in contract["notes"]
    assert "destructive reverse" in contract["notes"]


def test_mutable_template_is_not_named_as_retained_evidence():
    directory = Path("team-4-aws-kinesis-sqs-messaging-v1-evidence")
    assert (directory / "evidence-template.json").exists()
    assert not (directory / "evidence.json").exists()


def test_historical_evidence_terminal_is_not_current_metadata():
    source = Path("scripts/release/check_release_metadata.py").read_text()
    assert 'ROOT.glob("**/evidence.json")' not in source
    # Historical envelopes retain their producer-SHA terminal; only current
    # release manifests/templates materialised at HEAD are current metadata.
    historical = {"producer_sha": "b" * 40, "terminal_migration": "0032_team2_data_slo_production_runtime"}
    assert historical["terminal_migration"] != migrations()[-1].migration_id
