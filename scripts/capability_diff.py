#!/usr/bin/env python3
"""Report semantically relevant changes between two ledger revisions."""

import argparse
import subprocess

import yaml

ORDER = ["not_started", "scaffold", "foundation", "functional_unvalidated", "validated"]


def load(ref, path):
    return yaml.safe_load(subprocess.check_output(["git", "show", f"{ref}:{path}"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("head", nargs="?", default="HEAD")
    p.add_argument("--path", default="docs/product/capability-ledger.yaml")
    a = p.parse_args()
    old = {x["id"]: x for x in load(a.base, a.path)["capabilities"]}
    new = {x["id"]: x for x in load(a.head, a.path)["capabilities"]}
    out = {
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "promoted": [],
        "demoted": [],
        "evidence changes": [],
        "blocker changes": [],
        "release-readiness changes": [],
    }
    for k in sorted(old.keys() & new.keys()):
        if old[k]["state"] != new[k]["state"] and old[k]["state"] in ORDER and new[k]["state"] in ORDER:
            out["promoted" if ORDER.index(new[k]["state"]) > ORDER.index(old[k]["state"]) else "demoted"].append(k)
        for label, key in [
            ("evidence changes", "evidence"),
            ("blocker changes", "blockers"),
            ("release-readiness changes", "release_readiness"),
        ]:
            if old[k][key] != new[k][key]:
                out[label].append(k)
    for k, v in out.items():
        print(f'{k}: {", ".join(v) if v else "none"}')


if __name__ == "__main__":
    main()
