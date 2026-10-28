import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.certification.check_executed_junit import validate
from scripts.release.verify_beta_candidate import read_evidence_archive


def archive(content=b"actual executed results", checksum=None, inventory=True):
    evidence = {
        "artifact_inventory": (
            [{"path": "evidence/run.xml", "sha256": checksum or hashlib.sha256(content).hexdigest()}]
            if inventory
            else []
        )
    }
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as output:
        output.writestr("evidence.json", json.dumps(evidence))
        output.writestr("run.xml", content)
    return data.getvalue()


def test_canonical_archive_verifier_checks_actual_supporting_bytes():
    assert read_evidence_archive(archive(), require_inventory=True)["artifact_inventory"]
    with pytest.raises(ValueError, match="checksum"):
        read_evidence_archive(archive(checksum="0" * 64), require_inventory=True)
    with pytest.raises(ValueError, match="empty"):
        read_evidence_archive(archive(inventory=False), require_inventory=True)


@pytest.mark.parametrize(
    "body",
    [
        "<testsuite tests='0'/>",
        "<broken",
        "<testsuite tests='1'><testcase><skipped/></testcase></testsuite>",
        "<testsuite tests='1'><testcase><failure/></testcase></testsuite>",
        "<testsuite tests='2'><testcase/></testsuite>",
    ],
)
def test_mandatory_junit_never_promotes_empty_failed_or_skipped_runs(tmp_path: Path, body):
    path = tmp_path / "run.xml"
    path.write_text(body)
    with pytest.raises(Exception):
        validate(path)


def test_mandatory_junit_accepts_executed_success(tmp_path):
    path = tmp_path / "run.xml"
    path.write_text("<testsuites><testsuite tests='1'><testcase name='actual-test'/></testsuite></testsuites>")
    validate(path)
