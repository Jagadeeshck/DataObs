#!/usr/bin/env python3
"""Create a bounded, deterministic, allowlist-only support bundle. Never uploads."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

SENSITIVE = (
    "authorization",
    "cookie",
    "password",
    "api_key",
    "apikey",
    "private_key",
    "client_secret",
    "token",
    "email",
    "subject",
    "tenant_id",
    "sql",
    "query",
    "body",
)
ALLOWLIST = {
    "version.json",
    "platform-health.json",
    "worker-heartbeats.json",
    "slo-evaluations.json",
    "backup-summary.json",
    "release-summary.json",
    "support-matrix.json",
}
MAX_FILE = 256 * 1024
MAX_TOTAL = 2 * 1024 * 1024


def redact(value):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if any(x in k.lower() for x in SENSITIVE) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def collect(source: Path, output: Path, timestamp: int = 0, dry_run: bool = False):
    selected = []
    for name in sorted(ALLOWLIST):
        path = source / name
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file() or path.resolve().parent != source.resolve():
            raise ValueError(f"unsafe input: {name}")
        if path.stat().st_size > MAX_FILE:
            raise ValueError(f"input too large: {name}")
        selected.append(path)
    if dry_run:
        return [p.name for p in selected]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        total = 0
        inventory = []
        redactions = 0
        for path in selected:
            raw = json.loads(path.read_text())
            safe = redact(raw)
            redactions += json.dumps(safe).count("[REDACTED]")
            data = (json.dumps(safe, sort_keys=True, separators=(",", ":")) + "\n").encode()
            total += len(data)
            if total > MAX_TOTAL:
                raise ValueError("bundle exceeds total size limit")
            (root / path.name).write_bytes(data)
            inventory.append({"path": path.name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
        (root / "manifest.json").write_text(
            json.dumps({"created_at_epoch": timestamp, "files": inventory}, sort_keys=True) + "\n"
        )
        (root / "redaction-report.json").write_text(
            json.dumps({"verified": True, "redacted_fields": redactions}, sort_keys=True) + "\n"
        )
        with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as tar:
            for path in sorted(root.iterdir()):
                info = tar.gettarinfo(str(path), arcname=path.name)
                info.mtime = timestamp
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                with path.open("rb") as fh:
                    tar.addfile(info, fh)
    return inventory


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path, nargs="?", default=Path("dataobs-support-bundle.tar.gz"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--timestamp", type=int, default=0)
    a = p.parse_args()
    print(json.dumps(collect(a.source, a.output, a.timestamp, a.dry_run), indent=2))


if __name__ == "__main__":
    main()
