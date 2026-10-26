from pathlib import Path

import pytest

from scripts.release.release_metadata import terminal_migration
from scripts.release.verify_release_authorization import validate

ROOT = Path(__file__).parents[2]
SHA = "a" * 40


def authorization(**updates):
    value = {
        "repository": "Jagadeeshck/DataObs",
        "producer_sha": SHA,
        "workflow_run_id": "42",
        "terminal_migration": terminal_migration(),
        "security_gate": "PASS",
        "beta_certification": "PASS",
        "supported_platform": "kubernetes-1.34",
        "release_authorized": True,
    }
    value.update(updates)
    return value


@pytest.mark.parametrize("tag", ["v0.2.0", "v0.2.0-beta.1", "v0.2.0-rc.1"])
def test_authorization_accepts_defined_tag_classes(tag):
    validate(authorization(), repository="Jagadeeshck/DataObs", sha=SHA, tag=tag, run_id="42")


@pytest.mark.parametrize(
    "change",
    [
        {"producer_sha": "b" * 40},
        {"security_gate": "INCOMPLETE"},
        {"security_gate": "UNVALIDATED"},
        {"security_gate": "FAIL"},
        {"beta_certification": "FAIL"},
        {"supported_platform": ""},
        {"release_authorized": False},
    ],
)
def test_authorization_fails_closed(change):
    with pytest.raises(ValueError):
        validate(authorization(**change), repository="Jagadeeshck/DataObs", sha=SHA, tag="v0.2.0", run_id="42")


def test_release_workflow_has_one_authority_and_safe_order():
    release = (ROOT / ".github/workflows/release.yml").read_text()
    candidate = (ROOT / ".github/workflows/beta-1-release-candidate.yml").read_text()
    assert "verify_certification.py" not in release
    assert "dataobs-release-authorization" in release and "verify_release_authorization.py" in release
    assert release.index("Validate immutable authorization") < release.index("docker/login-action")
    assert release.index("Fail on critical vulnerabilities") < release.index("docker/login-action")
    assert "current_terminal_migration.py --json" in release
    assert "name: dataobs-release-authorization" in candidate
    assert candidate.index("--enforce") < candidate.index("release_authorized':True")
    assert (
        "Independent evidence verification" not in (ROOT / ".github/workflows/beta-security-hardening.yml").read_text()
    )


def test_invalid_and_ambiguous_authority_are_rejected_by_contract():
    with pytest.raises(ValueError):
        validate(authorization(), repository="Jagadeeshck/DataObs", sha=SHA, tag="latest", run_id="42")
    release = (ROOT / ".github/workflows/release.yml").read_text()
    assert "runs.length !== 1" in release
