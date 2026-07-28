import urllib.parse

import pytest

from scripts.release.verify_certification import (
    CertificationError,
    verify_certification,
)

SHA = "a" * 40


def _run(**overrides):
    value = {
        "id": 42,
        "html_url": "https://github.example/runs/42",
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
    }
    value.update(overrides)
    return value


def _verify(runs):
    calls = []

    def get(url, token):
        calls.append((url, token))
        return {"workflow_runs": runs}

    result = verify_certification("owner/repo", SHA, token="secret", workflows=(("CI", "ci.yml"),), get=get)
    return result, calls


def test_accepts_one_exact_completed_success_and_returns_metadata():
    result, calls = _verify([_run()])
    assert result == [{"workflow": "CI", "id": 42, "url": "https://github.example/runs/42"}]
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(calls[0][0]).query)
    assert query == {"head_sha": [SHA], "status": ["completed"], "per_page": ["100"]}


@pytest.mark.parametrize(
    "runs",
    [
        [],
        [_run(head_sha="b" * 40)],
        [_run(status="queued")],
        [_run(conclusion="cancelled")],
        [_run(conclusion="skipped")],
        [_run(conclusion="neutral")],
    ],
)
def test_rejects_missing_stale_or_unsuccessful_runs(runs):
    with pytest.raises(CertificationError):
        _verify(runs)


def test_rejects_duplicate_successful_candidates():
    with pytest.raises(CertificationError, match="found 2"):
        _verify([_run(), _run(id=43)])


def test_rejects_invalid_inputs_before_request():
    with pytest.raises(ValueError):
        verify_certification("invalid", SHA, token="secret", get=lambda *_: {})
    with pytest.raises(ValueError):
        verify_certification("owner/repo", "short", token="secret", get=lambda *_: {})
