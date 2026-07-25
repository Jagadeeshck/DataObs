#!/usr/bin/env python3
"""Report every semantically relevant capability-ledger change."""

from __future__ import annotations

import argparse
import subprocess
import sys

import yaml

ORDER = ["not_started", "scaffold", "foundation", "functional_unvalidated", "validated"]
SPECIAL = {"deprecated", "optional_integration"}
SECTIONS = [
    "added",
    "removed",
    "promoted",
    "demoted",
    "moved_to_deprecated",
    "moved_to_optional_integration",
    "restored_from_deprecated",
    "restored_from_optional_integration",
    "other_state_changes",
    "evidence_changes",
    "blocker_changes",
    "release_readiness_changes",
]


def load(ref: str, path: str, *, missing_ok: bool = False) -> dict:
    result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    if result.returncode:
        # A valid revision without a ledger is the supported first-ledger bootstrap.
        valid_ref = (
            subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], capture_output=True).returncode == 0
        )
        if missing_ok and valid_ref:
            return {"capabilities": []}
        raise ValueError(f"cannot read ledger at base reference {ref!r}")
    return yaml.safe_load(result.stdout)


def diff(old_data: dict, new_data: dict) -> dict[str, list[str]]:
    old = {x["id"]: x for x in old_data.get("capabilities", [])}
    new = {x["id"]: x for x in new_data.get("capabilities", [])}
    out = {section: [] for section in SECTIONS}
    out["added"] = sorted(new.keys() - old.keys())
    out["removed"] = sorted(old.keys() - new.keys())
    for cid in sorted(old.keys() & new.keys()):
        before, after = old[cid]["state"], new[cid]["state"]
        if before != after:
            if after == "deprecated":
                section = "moved_to_deprecated"
            elif after == "optional_integration":
                section = "moved_to_optional_integration"
            elif before == "deprecated":
                section = "restored_from_deprecated"
            elif before == "optional_integration":
                section = "restored_from_optional_integration"
            elif before in ORDER and after in ORDER:
                section = "promoted" if ORDER.index(after) > ORDER.index(before) else "demoted"
            else:
                section = "other_state_changes"
            out[section].append(cid)
        for section, key in [
            ("evidence_changes", "evidence"),
            ("blocker_changes", "blockers"),
            ("release_readiness_changes", "release_readiness"),
        ]:
            if old[cid].get(key) != new[cid].get(key):
                out[section].append(cid)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", nargs="?")
    parser.add_argument("head", nargs="?", default="HEAD")
    parser.add_argument("--base-ref", dest="base_ref")
    parser.add_argument("--path", default="docs/product/capability-ledger.yaml")
    args = parser.parse_args()
    base = args.base_ref or args.base
    if not base:
        parser.error("a base revision or --base-ref is required")
    try:
        report = diff(load(base, args.path, missing_ok=True), load(args.head, args.path))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for section in SECTIONS:
        values = report[section]
        print(f'{section}: {", ".join(values) if values else "none"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
