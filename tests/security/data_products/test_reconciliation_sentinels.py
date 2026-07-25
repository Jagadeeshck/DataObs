"""Positive sentinel injection through the production redactor."""

import json
from datetime import datetime, timezone

from scripts.certification.provenance import certification_commit_sha
from scripts.certification.redact_artifacts import SENTINELS, redact


def test_foundation_sentinels_are_actually_redacted(
    security_client, security_evidence_dir, foundation_security_files, request
):
    started = datetime.now(timezone.utc)
    raw = b"\n".join(SENTINELS)
    fixtures = [security_evidence_dir / "redacted.log", security_evidence_dir / "sentinel-input.json"]
    security_evidence_dir.mkdir(parents=True, exist_ok=True)
    fixtures[0].write_bytes(b"controlled log\n" + raw)
    fixtures[1].write_text(json.dumps({"cli_output": raw.decode()}))
    injected = sum(path.read_bytes().count(sentinel) for path in fixtures for sentinel in SENTINELS)
    redacted = redact(security_evidence_dir)
    remaining = sum(path.read_bytes().count(sentinel) for path in fixtures for sentinel in SENTINELS)
    assert injected > 0 and redacted == injected and remaining == 0
    captured_source_bytes = fixtures[1].stat().st_size
    fixtures[1].unlink()  # controlled source is not retained; redacted.log is.
    assert captured_source_bytes > 0 and not fixtures[1].exists()
    completed = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "commit_sha": certification_commit_sha(),
        "elasticsearch_version": security_client.info()["version"]["number"],
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        # The workflow performs the final scan after pytest has written JUnit.
        "files_scanned": len(foundation_security_files),
        "sentinels_injected": injected,
        "sentinels_redacted": redacted,
        "sentinels_remaining": remaining,
        "test_names": [request.node.nodeid],
        "result": "passed",
    }
    (security_evidence_dir / "sentinel-report.json").write_text(json.dumps(report, indent=2) + "\n")
