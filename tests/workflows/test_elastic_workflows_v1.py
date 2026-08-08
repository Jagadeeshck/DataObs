from pathlib import Path

import pytest

from integrations.elastic.kibana.configuration import KibanaConfiguration
from integrations.elastic.workflows.execution_sync import normalize_status
from integrations.elastic.workflows.validator import validate_managed_definitions, validate_workflow


def test_space_mapping_is_server_owned() -> None:
    config = KibanaConfiguration("https://kibana.example", spaces={"production": "dataobs-prod"})
    assert config.space_for("production") == "dataobs-prod"
    with pytest.raises(ValueError):
        config.space_for("attacker-space")


def test_managed_workflow_is_reviewed_and_uses_cases_steps() -> None:
    pack = validate_managed_definitions()
    assert [item["id"] for item in pack] == ["dataobs-incident-case-triage-v1"]


@pytest.mark.parametrize("step", ["kibana.request", "http", "cases.deleteCases", "unknown.step"])
def test_unsafe_workflow_step_is_rejected(tmp_path: Path, step: str) -> None:
    path = tmp_path / "unsafe.yaml"
    path.write_text(f"id: unsafe\nsteps:\n  - id: unsafe\n    type: {step}\n")
    with pytest.raises(ValueError):
        validate_workflow(path)


@pytest.mark.parametrize(
    ("provider", "domain"),
    [("waiting_for_input", "waiting_for_input"), ("timed_out", "timed_out"), ("brand_new", "provider_status_unknown")],
)
def test_status_normalization(provider: str, domain: str) -> None:
    assert normalize_status(provider) == domain
