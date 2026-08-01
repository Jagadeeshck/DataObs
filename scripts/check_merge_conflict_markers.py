#!/usr/bin/env python3
"""Fail when tracked text files contain unresolved merge-conflict markers."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKERS = (
    re.compile(r"^" + re.escape("<" * 7) + r"(?: .*)?$"),
    re.compile(r"^" + re.escape("=" * 7) + r"$"),
    re.compile(r"^" + re.escape(">" * 7) + r"(?: .*)?$"),
)


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8", errors="strict")
    return [ROOT / item for item in output.split("\0") if item]


def conflicts() -> list[str]:
    findings: list[str] = []
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.fullmatch(line) for pattern in MARKERS):
                findings.append(f"{path.relative_to(ROOT)}:{line_number}: {line}")
    return findings


def main() -> int:
    findings = conflicts()
    if findings:
        print("Unresolved merge-conflict markers found:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("merge-conflict marker check: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
