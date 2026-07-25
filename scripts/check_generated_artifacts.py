"""Fail CI when reproducible dependency/build/browser output is committed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import PurePosixPath

FORBIDDEN_PARTS = {"node_modules", "playwright-report", "test-results", "coverage", ".playwright"}
FORBIDDEN_PREFIXES = ("ui/dataobs-console/dist/", "ui/dataobs-console/.vite/")


def tracked_generated_files() -> list[str]:
    output = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True).stdout.decode(
        "utf-8", errors="strict"
    )
    paths = (path for path in output.split("\0") if path)
    return sorted(
        path
        for path in paths
        if FORBIDDEN_PARTS.intersection(PurePosixPath(path).parts) or path.startswith(FORBIDDEN_PREFIXES)
    )


def main() -> int:
    offenders = tracked_generated_files()
    if offenders:
        print("Tracked generated artifacts are forbidden:", *offenders, sep="\n  ", file=sys.stderr)
        return 1
    print("generated-artifact policy: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
