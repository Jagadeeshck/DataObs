#!/usr/bin/env python3
"""Compare migration identities, checksums and dependency order to a Git base."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def plan(ref: str) -> list[dict]:
    source = subprocess.run(
        ["git", "show", f"{ref}:docs/product/capability-ledger.yaml"],
        capture_output=True,
    )
    valid = subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], capture_output=True)
    if valid.returncode:
        raise ValueError(f"invalid base reference {ref!r}")
    if source.returncode:
        return []  # explicit initial-repository bootstrap
    import yaml

    data = yaml.safe_load(source.stdout)
    checksums = data.get("migration_checksums", {})
    # The checksum registry is append-only and ordered by the executable plan.
    # Capability chains can legitimately mention only the migrations relevant to
    # that capability, so using the longest chain silently omitted later entries.
    released = list(checksums)
    return [
        {"migration_id": mid, "checksum": checksums.get(mid), "dependencies": released[:i]}
        for i, mid in enumerate(released)
    ]


def current_plan() -> list[dict]:
    output = subprocess.check_output([sys.executable, "-m", "packages.elastic_store.cli", "plan"])
    return json.loads(output)["migrations"]


def check(old: list[dict], new: list[dict]) -> list[str]:
    errors: list[str] = []
    old_ids, new_ids = [m["migration_id"] for m in old], [m["migration_id"] for m in new]
    if new_ids[: len(old_ids)] != old_ids:
        missing = sorted(set(old_ids) - set(new_ids))
        errors.append(f"existing migration order changed; missing IDs: {', '.join(missing) or 'none'}")
    new_by_id = {m["migration_id"]: m for m in new}
    for migration in old:
        mid = migration["migration_id"]
        if mid not in new_by_id:
            continue
        if migration.get("checksum") != new_by_id[mid].get("checksum"):
            errors.append(f"migration checksum changed: {mid}")
        old_deps = migration.get("dependencies", [])
        new_deps = new_by_id[mid].get("dependencies", [])
        # Older ledgers encode order rather than the registry's immediate dependency.
        if old_deps and old_deps[-1:] != new_deps[-1:]:
            errors.append(f"migration dependency changed: {mid}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--allow-bootstrap", action="store_true")
    args = parser.parse_args()
    try:
        old = plan(args.base_ref)
        if not old and not args.allow_bootstrap:
            raise ValueError("base has no migration ledger; rerun with --allow-bootstrap for initial bootstrap")
        errors = check(old, current_plan())
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"migration immutability passed: {len(old)} released migrations unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
