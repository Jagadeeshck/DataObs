#!/usr/bin/env python3
"""Report the terminal migration from the executable migration registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.validate_migration_graph import validate


def migration_report() -> dict[str, Any]:
    registry = migrations()
    if not registry:
        raise ValueError("migration registry is empty")
    ids = [migration.migration_id for migration in registry]
    if len(ids) != len(set(ids)):
        raise ValueError("migration registry contains duplicate IDs")
    numeric_prefixes = [migration_id.split("_", 1)[0] for migration_id in ids]
    duplicate_prefixes = sorted(
        {prefix for prefix in numeric_prefixes if numeric_prefixes.count(prefix) > 1}
    )
    if duplicate_prefixes:
        raise ValueError(
            "migration registry contains duplicate numeric prefixes: "
            + ", ".join(duplicate_prefixes)
        )
    previous: str | None = None
    for migration in registry:
        expected = [] if previous is None else [previous]
        if list(migration.dependencies) != expected:
            raise ValueError(
                f"invalid migration ordering at {migration.migration_id}: "
                f"expected dependencies {expected}, got {migration.dependencies}"
            )
        previous = migration.migration_id
    checksum = hashlib.sha256(
        json.dumps(
            [{"id": migration.migration_id, "checksum": migration.checksum} for migration in registry],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return {
        "migration_count": len(ids),
        "terminal_migration": graph["terminal_migration"],
        "ordered_migration_ids": ids,
        "registry_checksum": checksum,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = migration_report()
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report["terminal_migration"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
