#!/usr/bin/env python3
"""Create a bounded, deterministic, allowlist-only support bundle. Never uploads."""

from __future__ import annotations

import argparse
import gzip
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
    "support-status.json",
    "components.json",
    "migrations.json",
    "error-budgets.json",
    "diagnostics.json",
    "configuration-fingerprint.json",
    "maintenance-state.json",
    "known-issues.json",
}
MAX_FILE = 256 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_LIST_ITEMS = 500
MAX_DEPTH = 12
MAX_STRING = 8192


def redact(value, path="$", depth=0, findings=None):
    findings = findings if findings is not None else []
    if depth > MAX_DEPTH:
        raise ValueError("maximum nesting depth exceeded")
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if any(x in k.lower() for x in SENSITIVE):
                fingerprint = hashlib.sha256(str(v).encode()).hexdigest()[:12]
                rule = next(x for x in SENSITIVE if x in k.lower())
                findings.append({"rule": rule, "path": f"{path}.{k}", "safe_fingerprint": f"sha256:{fingerprint}"})
                result[k] = "[REDACTED]"
            else:
                result[k] = redact(v, f"{path}.{k}", depth + 1, findings)
        return result
    if isinstance(value, list):
        if len(value) > MAX_LIST_ITEMS:
            raise ValueError("maximum list items exceeded")
        return [redact(v, f"{path}[{i}]", depth + 1, findings) for i, v in enumerate(value)]
    if isinstance(value, str) and len(value) > MAX_STRING:
        raise ValueError("maximum string length exceeded")
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
        findings = []
        for path in selected:
            raw = json.loads(path.read_text())
            safe = redact(raw, path=f"$.{path.name}", findings=findings)
            data = (json.dumps(safe, sort_keys=True, separators=(",", ":")) + "\n").encode()
            total += len(data)
            if total > MAX_TOTAL:
                raise ValueError("bundle exceeds total size limit")
            (root / path.name).write_bytes(data)
            inventory.append({"path": path.name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
        identity = next((json.loads(p.read_text()) for p in selected if p.name == "version.json"), {})
        bundle_id = hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()
        manifest = {
            "bundle_schema_version": "2.0",
            "created_at_epoch": timestamp,
            "dataobs_version": identity.get("version", "unknown"),
            "release_sha": identity.get("release_sha", "unknown"),
            "terminal_migration": identity.get("terminal_migration", "unknown"),
            "included_sections": [x["path"] for x in inventory],
            "excluded_sections": sorted(ALLOWLIST - {x["path"] for x in inventory}),
            "checksums": {x["path"]: x["sha256"] for x in inventory},
            "redaction_result": "pass",
            "bundle_id": f"sha256:{bundle_id}",
            "files": inventory,
        }
        (root / "support-bundle-manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
        (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
        (root / "redaction-report.json").write_text(
            json.dumps({"verified": True, "redacted_fields": len(findings), "findings": findings}, sort_keys=True)
            + "\n"
        )
        with output.open("wb") as raw_output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=timestamp) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
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
