#!/usr/bin/env python3
"""Verify retained artifacts are bounded, relative and sentinel-free."""

from __future__ import annotations

import argparse
from pathlib import Path

SENTINELS = (
    b"DATAOBS_CERT_SENTINEL_DB_PASSWORD",
    b"DATAOBS_CERT_SENTINEL_KAFKA_SECRET",
    b"DATAOBS_CERT_SENTINEL_WEBHOOK_TOKEN",
    b"DATAOBS_CERT_SENTINEL_API_KEY",
)

MAX_BYTES = 100 * 1024 * 1024


def verify(root: Path) -> list[str]:
    errors = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if path.stat().st_size > MAX_BYTES:
            errors.append(f"artifact exceeds 100 MiB: {relative}")
        data = path.read_bytes()
        if any(value in data for value in SENTINELS):
            errors.append(f"sentinel remains: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    errors = verify(args.root)
    if errors:
        print("\n".join(f"ERROR: {x}" for x in errors))
        return 1
    print("artifact verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
