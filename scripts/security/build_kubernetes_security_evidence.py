#!/usr/bin/env python3
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--sha", required=True)
p.add_argument("--input", action="append", default=[])
p.add_argument("--output", default="team-0-kubernetes-runtime-security-v1-evidence")
a = p.parse_args()
out = Path(a.output)
out.mkdir(parents=True, exist_ok=True)
files = {}
for item in a.input:
    src = Path(item)
    dst = out / src.name
    dst.write_bytes(src.read_bytes())
    files[dst.name] = hashlib.sha256(dst.read_bytes()).hexdigest()
meta = {
    "schema_version": "1.0",
    "target_sha": a.sha,
    "terminal_migration": subprocess.check_output(
        ["python", "scripts/release/current_terminal_migration.py"], text=True
    ).strip(),
    "hosted_cluster": "PENDING",
    "kind_functional": "PENDING",
    "release_decision": "PENDING" if not files else "BLOCKED_UNTIL_HOSTED_WHEN_REQUIRED",
    "tool_versions": {"python": platform.python_version()},
    "files": files,
}
(out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
