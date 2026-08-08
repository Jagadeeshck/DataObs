from pathlib import Path

import pytest

from integrations.elastic.workflows.validator import validate_workflow


def write(tmp_path: Path, steps: str) -> Path:
    path = tmp_path / "workflow.yaml"
    path.write_text("id: test\nsteps:\n" + steps)
    return path


@pytest.mark.parametrize("steps", ["  - hello\n", "  - 123\n", "  - null\n", "  - type: cases.getCase\n  - shell\n"])
def test_malformed_top_level_workflow_step_rejected(tmp_path, steps) -> None:
    with pytest.raises(ValueError):
        validate_workflow(write(tmp_path, steps))


def test_malformed_nested_workflow_step_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        validate_workflow(
            write(tmp_path, "  - type: condition\n    then:\n      - type: cases.addComment\n      - shell\n")
        )


def test_deeply_nested_forbidden_workflow_step_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        validate_workflow(
            write(
                tmp_path,
                "  - type: condition\n    then:\n      - type: condition\n        else:\n          - type: exec\n",
            )
        )
