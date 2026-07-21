#!/usr/bin/env python3
"""Redact bounded text artifacts and fail closed for binary sentinel matches."""

from __future__ import annotations

import argparse
from pathlib import Path

SENTINELS = (
    b"DATAOBS_CERT_SENTINEL_DB_PASSWORD",
    b"DATAOBS_CERT_SENTINEL_KAFKA_SECRET",
    b"DATAOBS_CERT_SENTINEL_WEBHOOK_TOKEN",
    b"DATAOBS_CERT_SENTINEL_API_KEY",
)
REDACTABLE = {".json", ".xml", ".log", ".txt", ".har", ".html", ".yaml", ".yml"}


def redact(root: Path) -> int:
    count = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        data = path.read_bytes()
        hits = [value for value in SENTINELS if value in data]
        if hits and path.suffix.lower() not in REDACTABLE:
            raise ValueError(f"sentinel found in non-redactable artifact: {path.relative_to(root)}")
        for value in hits:
            data = data.replace(value, b"[REDACTED]")
            count += 1
        if hits:
            path.write_bytes(data)
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(f"redaction complete: {redact(args.root)} sentinel occurrence(s) removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
