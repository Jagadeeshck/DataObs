#!/usr/bin/env python3
"""Render a gate decision; optionally enforce production authorization."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def create(posture: Path, output: Path, run_id: str) -> dict:
    report = json.loads(posture.read_text())
    state = report["overall_state"]
    if state not in {"PASS", "INCOMPLETE", "UNVALIDATED", "FAIL"}:
        raise ValueError(f"invalid posture state: {state}")
    gate = {
        "schema_version": "1.1",
        "repository": report["repository"],
        "sha": report["sha"],
        "workflow_run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state": state,
        "release_authorized": state == "PASS",
    }
    output.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    return gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--posture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow-run-id", default="")
    parser.add_argument("--enforce", action="store_true", help="fail unless state is PASS")
    args = parser.parse_args()
    gate = create(args.posture, args.output, args.workflow_run_id)
    return int(args.enforce and gate["state"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
