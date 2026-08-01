#!/usr/bin/env python3
"""Fail closed when active release surfaces use an unexplained Team 6 identity."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY = re.compile(r"(?i)\bteam[ -]?6\b|team-6-")
ACTIVE_ROOTS = (
    ".github/workflows",
    "scripts/release",
    "scripts/certification",
    "scripts/operations",
    "docs/release",
    "docs/operations",
    "docs/security",
)
ALLOWED = {
    Path("docs/release/beta-1-certification-manifest.yaml"),
    Path("docs/release/team-0-release-process.md"),
    Path("scripts/release/validate_team0_naming.py"),
}


def violations(root: Path = ROOT) -> list[str]:
    result: list[str] = []
    for base_name in ACTIVE_ROOTS:
        base = root / base_name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            relative = path.relative_to(root)
            if not path.is_file() or "__pycache__" in path.parts or relative in ALLOWED or "audit" in path.name.lower():
                continue
            for number, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                if LEGACY.search(line):
                    result.append(f"{relative}:{number}: unexplained legacy Team 6 identifier")
    return result


def main() -> int:
    errors = violations()
    if errors:
        print("\n".join(errors))
        return 1
    print("Team 0 naming contract validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
