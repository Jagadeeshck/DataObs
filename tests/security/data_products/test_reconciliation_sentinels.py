"""Positive sentinel injection through the production redactor."""

import json
import os
import subprocess
from datetime import datetime, timezone

from scripts.certification.redact_artifacts import SENTINELS, redact


def test_foundation_sentinels_are_actually_redacted(security_client, security_evidence_dir, request):
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
    fixtures[1].unlink()  # controlled source is not retained; redacted.log is.
    completed = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "commit_sha": os.getenv("GITHUB_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "elasticsearch_version": security_client.info()["version"]["number"],
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "files_scanned": len(fixtures),
        "sentinels_injected": injected,
        "sentinels_redacted": redacted,
        "sentinels_remaining": remaining,
        "test_names": [request.node.nodeid],
        "result": "passed",
    }
    (security_evidence_dir / "sentinel-report.json").write_text(json.dumps(report, indent=2) + "\n")
