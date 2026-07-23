#!/usr/bin/env python3
"""Assemble producer outputs without ambiguous overwrites."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from packages.elastic_store.manifest import DATA_PRODUCT_EVIDENCE_OWNERS


def assemble(downloaded: Path, retained: Path) -> None:
    retained.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for owner, expected in DATA_PRODUCT_EVIDENCE_OWNERS.items():
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


if __name__ == "__main__":
    assemble(Path(sys.argv[1]), Path(sys.argv[2]))
