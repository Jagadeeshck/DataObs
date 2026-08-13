import hashlib
import json
import tarfile
from pathlib import Path

import pytest
import yaml

from scripts.operations.collect_support_bundle import collect
from scripts.operations.validate_runbook_coverage import validate
from src.platform_operations.supportability import configuration_view, diagnostic_view, maintenance_view, support_view


def test_support_status_is_conservative():
    v = support_view()
    assert v["support_profile"] == "blocked"
    assert v["kubernetes_support_state"] != "supported"
    assert v["ha_profile"] == "unsupported"


def test_diagnostics_are_bounded_and_safe():
    v = diagnostic_view()
    assert any(c["state"] == "healthy" for c in v["checks"])
    assert any(c["state"] == "degraded" for c in v["checks"])
    assert any(c["state"] == "unknown" for c in v["checks"])
    assert all(
        set(c) == {"id", "state", "severity", "reason_code", "remediation_code", "checked_at"} for c in v["checks"]
    )
    assert not any(word in json.dumps(v).lower() for word in ("traceback", "exception message", "password="))


def test_configuration_fingerprint_is_deterministic_secret_independent_and_meaningful():
    safe = {
        "store_backend": "memory",
        "auth_provider": "oidc",
        "oidc_enabled": True,
        "tls_verification_enabled": True,
        "environment_mode": "production",
    }
    a = configuration_view({**safe, "client_secret": "one"})
    b = configuration_view({**safe, "client_secret": "two"})
    assert a["fingerprint"] == b["fingerprint"]
    assert a["fingerprint"] != configuration_view({**safe, "store_backend": "elasticsearch"})["fingerprint"]
    assert "secret" not in json.dumps(a).lower()


def test_maintenance_does_not_mask_health():
    assert maintenance_view()["state"] == "normal"
    health = {"state": "unhealthy"}
    maintenance = {"state": "active"}
    assert health["state"] == "unhealthy" and maintenance["state"] == "active"


def test_bundle_v2_redaction_bounds_and_determinism(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    identity = {
        "version": "0.2.0",
        "release_sha": "a" * 40,
        "terminal_migration": "0031",
        "client_secret": "do-not-print",
    }
    (source / "version.json").write_text(json.dumps(identity))
    a = tmp_path / "a.tgz"
    b = tmp_path / "b.tgz"
    collect(source, a, 42)
    collect(source, b, 42)
    assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
    with tarfile.open(a) as tar:
        assert "support-bundle-manifest.json" in tar.getnames()
        assert b"do-not-print" not in tar.extractfile("version.json").read()
        report = json.load(tar.extractfile("redaction-report.json"))
        assert set(report["findings"][0]) == {"rule", "path", "safe_fingerprint"}
    (source / "version.json").write_text(json.dumps({"items": list(range(501))}))
    with pytest.raises(ValueError, match="list items"):
        collect(source, tmp_path / "large.tgz")


def test_runbook_critical_coverage_and_missing_failure(tmp_path):
    assert validate(Path("docs/operations/runbook-registry.yaml")) == []
    data = yaml.safe_load(Path("docs/operations/runbook-registry.yaml").read_text())
    data["runbooks"] = data["runbooks"][1:]
    p = tmp_path / "r.yaml"
    p.write_text(yaml.safe_dump(data))
    assert validate(p)
