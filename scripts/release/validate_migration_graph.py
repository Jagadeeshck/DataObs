#!/usr/bin/env python3
"""Validate the executable migration DAG and emit a stable report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from packages.elastic_store.manifest import migrations


def validate(items=None, recorded_checksums=None):
    items = list(items if items is not None else migrations())
    errors = []
    ids = [m.migration_id for m in items]
    by_id = {m.migration_id: m for m in items}
    dup_ids = sorted({x for x in ids if ids.count(x) > 1})
    errors += [f"duplicate_id:{x}" for x in dup_ids]
    ordinals = [re.match(r"^(\d{4})_", x).group(1) if re.match(r"^(\d{4})_", x) else None for x in ids]
    errors += [f"duplicate_ordinal:{x}" for x in sorted({x for x in ordinals if x and ordinals.count(x) > 1})]
    for m in items:
        for dep in m.dependencies:
            if dep not in by_id:
                errors.append(f"unknown_dependency:{m.migration_id}:{dep}")
            elif ids.index(dep) >= ids.index(m.migration_id):
                errors.append(f"future_dependency:{m.migration_id}:{dep}")
    visiting = set()
    visited = set()

    def visit(mid):
        if mid in visiting:
            errors.append(f"dependency_cycle:{mid}")
            return
        if mid in visited or mid not in by_id:
            return
        visiting.add(mid)
        for dep in by_id[mid].dependencies:
            visit(dep)
        visiting.remove(mid)
        visited.add(mid)

    for mid in ids:
        visit(mid)
    depended = {d for m in items for d in m.dependencies}
    leaves = [x for x in ids if x not in depended]
    if len(leaves) > 1:
        errors.append("ambiguous_terminal:" + ",".join(leaves))
    for mid, checksum in (recorded_checksums or {}).items():
        if mid in by_id and by_id[mid].checksum != checksum:
            errors.append(f"checksum_mutation:{mid}")
    state = (
        "valid"
        if not errors
        else ("ambiguous" if all(e.startswith("ambiguous_terminal") for e in errors) else "invalid")
    )
    return {
        "state": state,
        "errors": errors,
        "terminal_migration": leaves[0] if len(leaves) == 1 else None,
        "leaves": leaves,
        "migration_count": len(items),
        "migrations": [
            {"id": m.migration_id, "ordinal": ordinals[i], "dependencies": list(m.dependencies), "checksum": m.checksum}
            for i, m in enumerate(items)
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output")
    a = p.parse_args()
    report = validate()
    data = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if a.output:
        Path(a.output).write_text(data)
    else:
        print(data, end="")
    return 0 if report["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
