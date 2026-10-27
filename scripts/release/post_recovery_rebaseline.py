#!/usr/bin/env python3
"""Build and validate the fail-closed post-recovery release baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40}$")
GATE_STATES = {"PASS", "FAIL", "PENDING", "BLOCKED_EXTERNAL", "NOT_APPLICABLE"}
PASS = "PASS"
MANDATORY_CAPABILITIES = {
    "foundation-backend",
    "foundation-console",
    "hosted-oidc",
    "hosted-tenant-isolation",
    "kubernetes",
    "elasticsearch",
    "kafka-stream-runtime",
    "browser",
    "accessibility",
    "backup",
    "restore",
    "dr",
    "sbom",
    "vulnerability",
    "licensing",
    "provenance",
    "signature",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def validate_candidate(sha: str, main_ref: str, expected_terminal: str) -> dict[str, Any]:
    if not SHA.fullmatch(sha):
        raise ValueError("candidate SHA must be an exact lowercase 40-character SHA")
    resolved = git("rev-parse", f"{sha}^{{commit}}")
    if resolved != sha:
        raise ValueError("candidate is ambiguous or does not resolve exactly")
    if subprocess.run(["git", "merge-base", "--is-ancestor", sha, main_ref], check=False).returncode:
        raise ValueError("candidate is not reachable from main")
    terminal = json.loads(
        subprocess.check_output(["python", "scripts/release/current_terminal_migration.py", "--json"], text=True)
    )["terminal_migration"]
    if terminal != expected_terminal:
        raise ValueError(f"terminal migration mismatch: {terminal} != {expected_terminal}")
    return {
        "repository": "Jagadeeshck/DataObs",
        "sha": sha,
        "parents": git("show", "-s", "--format=%P", sha).split(),
        "tree": git("show", "-s", "--format=%T", sha),
        "dataobs_version": "0.2.0",
        "chart_version": "0.2.0",
        "terminal_migration": terminal,
        "selected_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_item(item: dict[str, Any], candidate_sha: str, now: datetime) -> list[str]:
    errors: list[str] = []
    if item.get("exact_sha") != candidate_sha:
        errors.append("WRONG_SHA")
    expires = item.get("expires_at")
    if expires and datetime.fromisoformat(expires.replace("Z", "+00:00")) <= now:
        errors.append("EXPIRED")
    if item.get("verification_state") == "VERIFIED":
        required = {"workflow", "run_id", "run_attempt", "created_at", "checksum", "artifact_id", "local_path"}
        if not required <= {key for key, value in item.items() if value not in (None, "")}:
            errors.append("MISSING_VERIFICATION_METADATA")
        elif not Path(item["local_path"]).is_file():
            errors.append("MISSING_ARTIFACT")
        elif item["checksum"] != "sha256:" + hashlib.sha256(Path(item["local_path"]).read_bytes()).hexdigest():
            errors.append("CHECKSUM_MISMATCH")
        if item.get("mandatory_test_result") in {None, "not_run", "skipped", "fail"}:
            errors.append("MANDATORY_TEST_NOT_PASSING")
    return errors


def derive_gates(index: dict[str, Any], blockers: list[dict[str, Any]], candidate_sha: str) -> list[dict[str, Any]]:
    by_capability = {item["capability"]: item for item in index["evidence"]}
    gates = []
    blocker_gates = {item["gate"] for item in blockers if item["state"] != "RESOLVED"}
    for capability in sorted(MANDATORY_CAPABILITIES):
        evidence = by_capability.get(capability)
        result = "PENDING"
        reason = "EXACT_SHA_VERIFIED_EVIDENCE_MISSING"
        if capability in blocker_gates:
            result, reason = "FAIL", "ACTIVE_BLOCKER"
        elif evidence and not verify_item(evidence, candidate_sha, datetime.now(timezone.utc)):
            if evidence.get("verification_state") == "VERIFIED" and evidence.get("mandatory_test_result") == "pass":
                result, reason = PASS, "EXACT_SHA_EVIDENCE_VERIFIED"
        gates.append({"id": capability, "result": result, "reason_code": reason, "mandatory": True})
    return gates


def supported_platform(gates: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [gate["id"] for gate in gates if gate["mandatory"] and gate["result"] != PASS]
    return {"supported": [], "decision": "INCOMPLETE", "blocking_gates": missing}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--expected-terminal", required=True)
    parser.add_argument("--evidence-index", type=Path, required=True)
    parser.add_argument("--blockers", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    candidate = validate_candidate(args.candidate_sha, args.main_ref, args.expected_terminal)
    index = json.loads(args.evidence_index.read_text())
    blockers = json.loads(args.blockers.read_text())["blockers"]
    errors = {
        item["artifact"]: verify_item(item, args.candidate_sha, datetime.now(timezone.utc))
        for item in index["evidence"]
    }
    gates = derive_gates(index, blockers, args.candidate_sha)
    platform = supported_platform(gates)
    write_json(args.output_directory / "candidate.json", candidate)
    write_json(
        args.output_directory / "evidence-verification.json",
        {
            "candidate_sha": args.candidate_sha,
            "state": (
                "PASS"
                if not any(errors.values())
                and all(item.get("verification_state") == "VERIFIED" for item in index["evidence"])
                else "INCOMPLETE"
            ),
            "independently_verified_artifacts": 0,
            "artifact_errors": errors,
            "note": "GitHub metadata discovery is not independent archive verification.",
        },
    )
    write_json(args.output_directory / "release-gates.json", {"candidate_sha": args.candidate_sha, "gates": gates})
    write_json(args.output_directory / "supported-platform-evaluation.json", platform)
    write_json(
        args.output_directory / "final-release-decision.json",
        {
            "candidate_sha": args.candidate_sha,
            "state": "NO_GO",
            "go": False,
            "security_posture": "INCOMPLETE",
            "security_release_gate": "INCOMPLETE",
            "supported": [],
            "failed_checks": platform["blocking_gates"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
