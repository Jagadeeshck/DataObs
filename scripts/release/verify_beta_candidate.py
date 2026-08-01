#!/usr/bin/env python3
"""Validate Beta evidence for exactly one repository commit (never infer success)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_SCHEMAS = {"1"}


class CandidateError(ValueError):
    pass


def verify(manifest: dict[str, Any], bundle: dict[str, Any], repository: str, sha: str) -> dict[str, Any]:
    if len(sha) != 40 or any(c not in "0123456789abcdefABCDEF" for c in sha):
        raise CandidateError("target SHA must be a full commit SHA")
    results = []
    supplied = bundle.get("capabilities", [])
    for requirement in manifest.get("capabilities", []):
        capability_id = requirement["capability_id"]
        matches = [item for item in supplied if item.get("capability_id") == capability_id]
        mandatory = bool(requirement.get("mandatory_for_beta"))
        if requirement.get("exclusion") and not mandatory:
            results.append({"capability_id": capability_id, "status": "excluded"})
            continue
        if len(matches) != 1:
            status = "pending" if not matches else "fail"
            results.append(
                {"capability_id": capability_id, "status": status, "reason": "missing or ambiguous evidence"}
            )
            continue
        item = matches[0]
        evidence = item.get("evidence")
        checks = (
            item.get("repository") == repository,
            item.get("head_sha") == sha,
            item.get("status") == "completed",
            item.get("conclusion") == requirement.get("required_conclusion", "success"),
            item.get("workflow") == requirement["workflow"],
            item.get("artifact_name") == requirement["artifact_name"],
            isinstance(evidence, dict),
            isinstance(evidence, dict) and evidence.get("producer_sha") == sha,
            isinstance(evidence, dict) and str(evidence.get("schema_version")) in SUPPORTED_SCHEMAS,
            isinstance(evidence, dict) and evidence.get("terminal_migration") == manifest["terminal_migration"],
            isinstance(evidence, dict) and bool(evidence.get("test_summary")),
            isinstance(evidence, dict) and bool(evidence.get("versions")),
        )
        results.append({"capability_id": capability_id, "status": "pass" if all(checks) else "fail"})
    failed = [
        r
        for r in results
        if r["status"] in {"fail", "pending"}
        and next(x for x in manifest["capabilities"] if x["capability_id"] == r["capability_id"]).get(
            "mandatory_for_beta"
        )
    ]
    return {
        "schema_version": "1",
        "repository": repository,
        "target_sha": sha,
        "status": "pass" if not failed else "pending",
        "capabilities": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("docs/release/beta-1-certification-manifest.yaml"))
    parser.add_argument("--evidence-bundle", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    bundle = json.loads(args.evidence_bundle.read_text(encoding="utf-8"))
    report = verify(manifest, bundle, args.repository, args.target_sha)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
