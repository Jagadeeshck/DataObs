#!/usr/bin/env python3
"""Refresh active release gates without promoting historical/local evidence."""

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def render():
    inventory = yaml.safe_load((ROOT / "docs/release/v0.2.0-gate-0-blockers.yaml").read_text())
    path = ROOT / "docs/release/team-0-release-gates-v1.yaml"
    source = yaml.safe_load(path.read_text())
    # No candidate is frozen. Historical PASS rows cannot attest to the current
    # source, and no retained independent final-head bundle has been supplied.
    source["candidate_sha"] = None
    source["assessment_source_sha"] = inventory["audited_main_sha"]
    source["candidate_frozen"] = False
    for gate in source["gates"]:
        gate.update(
            result="PENDING",
            reason_code="EXACT_SHA_VERIFIED_EVIDENCE_MISSING",
            blocker=True,
            evidence_source="retained exact-SHA hosted/candidate artifact",
            remediation="Run current exact-SHA producers and the existing independent verifier before candidate freeze.",
        )
    return yaml.safe_dump(source, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "docs/release/team-0-release-gates-v1.yaml"
    value = render()
    if args.check:
        if path.read_text() != value:
            raise SystemExit("active release gates are stale; run canonical renderer")
    else:
        path.write_text(value)


if __name__ == "__main__":
    main()
