#!/usr/bin/env python3
"""Fail closed when release-facing metadata drifts from the executable registry."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.release.release_metadata import terminal_migration  # noqa: E402

TERMINAL_CLAIM = re.compile(
    r"(?i)terminal(?: migration)?(?: registry)?[^\n`]{0,80}`?(00\d{2}_[a-z0-9_]+)"
)


def main() -> int:
    expected = terminal_migration()
    manifest = yaml.safe_load((ROOT / "docs/release/beta-1-certification-manifest.yaml").read_text())
    errors: list[str] = []
    if manifest.get("terminal_migration") != expected:
        errors.append("certification manifest terminal migration differs from executable registry")
    checked = [ROOT / ".github/workflows/beta-1-release-candidate.yml"]
    checked += list((ROOT / "docs/product").glob("*.md"))
    for path in checked:
        for found in set(TERMINAL_CLAIM.findall(path.read_text(encoding="utf-8"))):
            if found != expected:
                errors.append(f"{path.relative_to(ROOT)} contains stale terminal migration {found}")
    for path in ROOT.glob("**/evidence.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        reported = value.get("terminal_migration")
        if reported is not None and reported != expected:
            errors.append(f"{path.relative_to(ROOT)} evidence terminal migration differs")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"release metadata matches executable terminal migration {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
