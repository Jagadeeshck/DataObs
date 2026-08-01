#!/usr/bin/env python3
"""Render secret-free, digest-pinned Helm image values from a release manifest."""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.current_terminal_migration import migration_report

REQUIRED = {
    "api",
    "console",
    "qualityWorker",
    "scannerWorker",
    "monitorRuntime",
    "pathwayWorker",
    "kafkaObserver",
    "otelCollector",
    "migrationJob",
}
DIGEST = re.compile(r"sha256:[0-9a-f]{64}$")


def render(manifest):
    components = manifest.get("components", {})
    missing = REQUIRED - components.keys()
    if missing:
        raise ValueError("missing required components: " + ", ".join(sorted(missing)))
    out = {}
    for name in sorted(REQUIRED):
        item = components[name]
        tag = item.get("image_tag", "")
        if tag.lower() == "latest":
            raise ValueError(f"{name}: latest is forbidden")
        if not DIGEST.fullmatch(item.get("image_digest", "")):
            raise ValueError(f"{name}: malformed digest")
        if not item.get("image_repository"):
            raise ValueError(f"{name}: missing repository")
        out[name] = {"image": {"repository": item["image_repository"], "tag": tag, "digest": item["image_digest"]}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    manifest = json.loads(a.manifest.read_text())
    if manifest.get("terminal_migration") != migration_report()["terminal_migration"]:
        raise SystemExit("unexpected terminal migration")
    try:
        result = render(manifest)
    except ValueError as e:
        raise SystemExit(str(e)) from e
    a.output.write_text(yaml.safe_dump(result, sort_keys=True))


if __name__ == "__main__":
    main()
