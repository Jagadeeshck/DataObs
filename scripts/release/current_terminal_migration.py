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
    graph = validate()
    if graph["state"] != "valid" or not graph["terminal_migration"]:
        raise ValueError(f"migration graph has no deterministic terminal: {graph['errors']}")
    ids = [item["id"] for item in graph["migrations"]]
    checksum = hashlib.sha256(json.dumps(graph["migrations"], sort_keys=True).encode()).hexdigest()
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
