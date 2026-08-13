#!/usr/bin/env python3
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    matrix = yaml.safe_load((ROOT / "docs/release/compatibility-matrix.yaml").read_text())
    upgrade = yaml.safe_load((ROOT / "docs/release/upgrade-policy.yaml").read_text())
    deps = yaml.safe_load((ROOT / "docs/release/deprecations.yaml").read_text())
    errors = []
    for dimension, entries in matrix.get("dimensions", {}).items():
        for entry in entries:
            if entry.get("state") not in {"supported", "compatible_but_unvalidated", "incompatible", "unknown"}:
                errors.append(f"{dimension}: invalid state")
    for item in deps.get("deprecations", []):
        if item["status"] not in {"planned", "active", "removed", "withdrawn"}:
            errors.append(f"{item['id']}: invalid status")
        if item.get("removal_version") and item["removal_version"] < item["deprecated_version"]:
            errors.append(f"{item['id']}: invalid version ordering")
    if upgrade.get("current_evidence", {}).get("supported_predecessor") is not None:
        errors.append("first release must not invent predecessor")
    print(json.dumps({"state": "invalid" if errors else "valid", "errors": errors}, indent=2))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
