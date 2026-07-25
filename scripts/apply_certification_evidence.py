#!/usr/bin/env python3
"""Validate certification evidence and propose (or explicitly apply) ledger evidence updates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = {
    "platform.migrations",
    "data.postgres",
    "streams.kafka",
    "incidents.replay",
    "integration.elastic",
    "console.validation",
}
REQUIRED = {
    "platform.migrations": {"migration-clean-install", "migration-upgrade"},
    "data.postgres": {"postgres-discovery", "postgres-isolation"},
    "streams.kafka": {"kafka-three-broker", "stream-api"},
    "incidents.replay": {"incident-exact-replay", "incident-corrected-replay"},
    "integration.elastic": {"elastic-real-stack"},
    "console.validation": {"playwright", "axe"},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("certification/evidence/capability-promotion-proposal.md"))
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text())
    schema = json.loads((ROOT / "certification/evidence-manifest.schema.json").read_text())
    jsonschema.validate(evidence, schema)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    hosted = bool(evidence.get("workflow_run_id") and evidence.get("workflow_run_url"))
    if hosted and evidence["commit_sha"] != head:
        print("ERROR: hosted evidence commit does not match HEAD", file=sys.stderr)
        return 1
    proposals = []
    for cid in sorted(CANDIDATES):
        item = evidence.get("capabilities", {}).get(cid)
        tests = set(item.get("tests", [])) if item else set()
        if item and item.get("status") == "passed" and REQUIRED[cid] <= tests and hosted:
            proposals.append(cid)
    lines = [
        "# Capability promotion proposal",
        "",
        f"Hosted evidence: **{'yes' if hosted else 'no'}**",
        "",
        "No capability is promoted merely because this harness exists.",
        "",
    ]
    lines += [f"- `{cid}`: eligible for human review" for cid in proposals] or [
        "- No capability currently qualifies for promotion."
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    if args.apply and not hosted:
        print("ERROR: local evidence cannot promote hosted-policy capabilities", file=sys.stderr)
        return 1
    if args.apply and proposals:
        ledger_path = ROOT / "docs/product/capability-ledger.yaml"
        ledger = yaml.safe_load(ledger_path.read_text())
        for cap in ledger["capabilities"]:
            if cap["id"] in proposals:
                # Evidence is attached, but release readiness deliberately remains blocked.
                cap["evidence"].setdefault("artifacts", []).append(evidence["workflow_run_url"])
        ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
