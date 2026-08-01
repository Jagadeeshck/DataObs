#!/usr/bin/env python3
"""Independently verify an RC manifest using only downloaded files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.release.current_terminal_migration import migration_report

SECRET = re.compile(
    r"(?i)(authorization:\s*bearer|api[_-]?key\s*[=:]|client[_-]?secret\s*[=:]|-----BEGIN .*PRIVATE KEY-----)"
)


def verify(manifest_path: Path, evidence_dir: Path) -> dict:
    m = json.loads(manifest_path.read_text())
    errors = []
    if m.get("publish_status") != "not_published":
        errors.append("publish status must be not_published")
    if not re.fullmatch(r"[0-9a-f]{40}", str(m.get("target_sha", ""))):
        errors.append("target SHA is invalid")
    migration = migration_report()
    if (
        m.get("terminal_migration") != migration["terminal_migration"]
        or m.get("migration_count") != migration["migration_count"]
    ):
        errors.append("migration registry metadata mismatch")
    for key in (
        "capability_evidence",
        "backup_restore_result",
        "upgrade_rollback_result",
        "HA_restart_result",
        "browser_result",
        "accessibility_result",
        "security_result",
    ):
        value = m.get(key)
        values = value if isinstance(value, list) else [value]
        if any(
            (isinstance(x, dict) and (x.get("mandatory", True) and x.get("status") != "pass"))
            or x in {"pending", "fail"}
            for x in values
        ):
            errors.append(f"mandatory result is not pass: {key}")
    for item in m.get("artifacts", []):
        path = evidence_dir / item["name"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            errors.append(f"artifact hash mismatch: {item['name']}")
    for path in evidence_dir.rglob("*"):
        if path.is_file() and SECRET.search(path.read_text(errors="ignore")):
            errors.append(f"possible secret in {path.name}")
    return {
        "schema_version": "1.1",
        "target_sha": m.get("target_sha"),
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.manifest, a.evidence_dir)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
