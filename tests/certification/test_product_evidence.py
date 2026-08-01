import argparse
import json
from pathlib import Path

import pytest

from scripts.certification.verify_product_evidence import EvidenceError, generate, verify


def xml(path: Path, *, failures=0, skipped=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<testsuite tests="1" failures="{failures}" errors="0" skipped="{skipped}"><testcase name="gate"/></testsuite>'
    )


def arguments(path, **changes):
    values = dict(
        directory=str(path),
        repository="Jagadeeshck/DataObs",
        workflow="job-run-backend",
        run_id="42",
        job_id="99",
        event="pull_request",
        elasticsearch_version="9.4.2",
        python_version="3.12.1",
        node_version="not-applicable",
        required_suite=["security", "tenant"],
        expected_sha=None,
    )
    values.update(changes)
    return argparse.Namespace(**values)


def test_generate_and_verify_exact_execution(tmp_path):
    xml(tmp_path / "results/tests.xml")
    args = arguments(tmp_path)
    generate(args)
    verify(args)


@pytest.mark.parametrize(
    "field,value", [("producer_sha", "0" * 40), ("workflow_run_id", "43"), ("elasticsearch_version", "9.4.1")]
)
def test_rejects_wrong_provenance(tmp_path, field, value):
    xml(tmp_path / "results/tests.xml")
    args = arguments(tmp_path)
    generate(args)
    metadata = json.loads((tmp_path / "metadata.json").read_text())
    metadata[field] = value
    (tmp_path / "metadata.json").write_text(json.dumps(metadata))
    with pytest.raises(EvidenceError):
        verify(args)


@pytest.mark.parametrize("failures,skipped", [(1, 0), (0, 1)])
def test_rejects_failure_or_security_skip(tmp_path, failures, skipped):
    xml(tmp_path / "results/tests.xml", failures=failures, skipped=skipped)
    args = arguments(tmp_path)
    generate(args)
    with pytest.raises(EvidenceError):
        verify(args)
