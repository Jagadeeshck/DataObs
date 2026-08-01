from copy import deepcopy

import pytest

from scripts.release.verify_beta_candidate import CandidateError, verify

SHA = "a" * 40
MANIFEST = {
    "terminal_migration": "0021",
    "capabilities": [
        {
            "capability_id": "security",
            "workflow": "security.yml",
            "artifact_name": "security-evidence",
            "required_conclusion": "success",
            "mandatory_for_beta": True,
        }
    ],
}


def valid():
    return {
        "capabilities": [
            {
                "capability_id": "security",
                "repository": "o/r",
                "head_sha": SHA,
                "status": "completed",
                "conclusion": "success",
                "workflow": "security.yml",
                "artifact_name": "security-evidence",
                "evidence": {
                    "producer_sha": SHA,
                    "schema_version": "1",
                    "terminal_migration": "0021",
                    "test_summary": {"tests": 1},
                    "versions": {"python": "3.11"},
                },
            }
        ]
    }


def test_exact_successful_run():
    assert verify(MANIFEST, valid(), "o/r", SHA)["status"] == "pass"


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "b" * 40),
        ("status", "cancelled"),
        ("conclusion", "failure"),
        ("workflow", "other.yml"),
        ("artifact_name", "wrong"),
    ],
)
def test_metadata_mismatch_fails(field, value):
    bundle = valid()
    bundle["capabilities"][0][field] = value
    assert verify(MANIFEST, bundle, "o/r", SHA)["status"] == "pending"


@pytest.mark.parametrize(
    "field,value",
    [
        ("producer_sha", "b" * 40),
        ("schema_version", "99"),
        ("terminal_migration", "old"),
        ("test_summary", None),
        ("versions", None),
    ],
)
def test_invalid_evidence_fails(field, value):
    bundle = valid()
    bundle["capabilities"][0]["evidence"][field] = value
    assert verify(MANIFEST, bundle, "o/r", SHA)["status"] == "pending"


def test_missing_and_ambiguous_runs_are_pending():
    assert verify(MANIFEST, {"capabilities": []}, "o/r", SHA)["status"] == "pending"
    bundle = valid()
    bundle["capabilities"].append(deepcopy(bundle["capabilities"][0]))
    assert verify(MANIFEST, bundle, "o/r", SHA)["status"] == "pending"


def test_bad_sha_rejected():
    with pytest.raises(CandidateError):
        verify(MANIFEST, valid(), "o/r", "short")
