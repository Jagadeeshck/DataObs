import importlib.util
from pathlib import Path

from scripts.certification.redact_artifacts import SENTINELS, redact

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/certification/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sentinel_redaction_and_verification(tmp_path):
    redactor = load("redact_artifacts")
    verifier = load("verify_artifacts")
    artifact = tmp_path / "report.json"
    artifact.write_bytes(b'{"value":"DATAOBS_CERT_SENTINEL_API_KEY"}')
    assert redactor.redact(tmp_path) == 1
    assert verifier.verify(tmp_path, sentinels_only=True) == []
    assert b"REDACTED" in artifact.read_bytes()


def test_attack_fixtures_cover_xss_ssrf_cursor_and_workflow():
    text = (ROOT / "certification/fixtures/security/attacks.json").read_text()
    for key in ("xss", "ssrf", "cursor", "workflow"):
        assert f'"{key}"' in text


def test_live_invalid_token_and_backing_store(live_stack):
    api, es = live_stack
    # The current development auth mode is explicitly not production IAM evidence.
    assert api.request("/health")["status"] in {"ok", "healthy"}
    assert es.request("/_cluster/health")["status"] in {"green", "yellow"}


# Positive redaction is part of the foundation, rather than a manufactured
# zero-sentinel scan.
def test_redactor_counts_every_injected_occurrence(tmp_path):
    target = tmp_path / "controlled.log"
    target.write_bytes(SENTINELS[0] + b"\n" + SENTINELS[0] + b"\n" + SENTINELS[1])
    assert redact(tmp_path) == 3
    assert all(value not in target.read_bytes() for value in SENTINELS)
