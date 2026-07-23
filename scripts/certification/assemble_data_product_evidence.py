#!/usr/bin/env python3
"""Assemble producer outputs without ambiguous overwrites."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from packages.elastic_store.manifest import data_product_evidence_inventory, data_product_evidence_owners


def assemble(downloaded: Path, retained: Path, *, profile: str) -> None:
    retained.mkdir(parents=True, exist_ok=True)
    if any(retained.iterdir()):
        raise ValueError("retained evidence directory must begin empty")
    seen: set[str] = set()
    owners = data_product_evidence_owners(profile)
    owned = {name for expected in owners.values() for name in expected}
    inventory = set(data_product_evidence_inventory(profile))
    if owned != inventory:
        raise ValueError(
            f"profile ownership differs from inventory: missing={sorted(inventory-owned)}, extra={sorted(owned-inventory)}"
        )
    for owner, expected in owners.items():
        source = downloaded / owner
        actual = {p.name for p in source.iterdir() if p.is_file()} if source.is_dir() else set()
        missing, unowned = set(expected) - actual, actual - set(expected)
        if missing or unowned:
            raise ValueError(f"{owner}: missing={sorted(missing)}, unowned={sorted(unowned)}")
        for name in expected:
            if name in seen or (retained / name).exists():
                raise ValueError(f"duplicate final basename: {name}")
            shutil.copy2(source / name, retained / name)
            seen.add(name)
    if seen != inventory:
        raise ValueError("assembled evidence does not exactly match the profile inventory")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("downloaded", type=Path)
    parser.add_argument("retained", type=Path)
    args = parser.parse_args()
    assemble(args.downloaded, args.retained, profile=args.profile)
