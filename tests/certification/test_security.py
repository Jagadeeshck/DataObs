import importlib.util
from pathlib import Path

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
    assert verifier.verify(tmp_path) == []
    assert b"REDACTED" in artifact.read_bytes()


def test_attack_fixtures_cover_xss_ssrf_cursor_and_workflow():
    text = (ROOT / "certification/fixtures/security/attacks.json").read_text()
    for key in ("xss", "ssrf", "cursor", "workflow"):
        assert f'"{key}"' in text
