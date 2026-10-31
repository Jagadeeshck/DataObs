#!/usr/bin/env python3
"""Dispatch or verify existing Gate 0 producers; never authorize publication."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.certification.provenance import expected_certification_sha  # noqa: E402
from scripts.release.verify_beta_candidate import verify_entry  # noqa: E402


def api(path, method="GET", fields=None):
    command = ["gh", "api", "--method", method, path]
    for key, value in (fields or {}).items():
        command += ["-f", f"{key}={value}"]
    output = subprocess.check_output(command)
    return json.loads(output) if output.strip() else {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["dispatch", "verify"])
    parser.add_argument("--sha", required=True)
    parser.add_argument("--ref")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sha = expected_certification_sha(args.sha)
    config = yaml.safe_load((ROOT / "docs/release/v0.2.0-gate-0-certification-manifest.yaml").read_text())
    repo = config["repository"]
    if args.phase == "dispatch":
        if not args.ref or api(f"repos/{repo}/commits/{args.ref}")["sha"] != sha:
            raise ValueError("dispatch ref must resolve to the exact independently supplied SHA")
        for workflow in sorted({e["workflow"] for e in config["capabilities"]}):
            api(f"repos/{repo}/actions/workflows/{workflow}/dispatches", "POST", {"ref": args.ref})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"target_sha": sha, "status": "dispatched_not_verified", "release_decision": "NO_GO"})
        )
        return 0
    results = []
    for source in config["capabilities"]:
        entry = {
            **source,
            "artifact": source["artifact"] + ("-" + sha if source.get("artifact_sha_suffix") else ""),
            "mandatory_for_beta": True,
            "evidence_schema_version": "1.0",
            "expected_elasticsearch_version": "9.4.2",
            "required_conclusion": "success",
            "accepted_events": ["push", "workflow_dispatch", "pull_request"],
        }
        runs = api(f"repos/{repo}/actions/workflows/{entry['workflow']}/runs?head_sha={sha}&per_page=100").get(
            "workflow_runs", []
        )
        artifacts = []
        for run in runs:
            artifacts.extend(api(f"repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100").get("artifacts", []))

        def load(artifact):
            # The canonical verifier reads the same downloaded envelope. Inspect
            # actual bytes too, so a producer cannot attest to absent supporting files.
            from scripts.release.verify_beta_candidate import read_evidence_archive

            raw = subprocess.check_output(["gh", "api", f"repos/{repo}/actions/artifacts/{artifact['id']}/zip"])
            value = read_evidence_archive(raw, require_inventory=True)
            if value.get("repository") != repo:
                raise ValueError("evidence repository mismatch")
            try:
                timestamp = datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - timestamp).total_seconds()
                if not 0 <= age <= 30 * 86400:
                    raise ValueError("evidence timestamp is stale or in the future")
            except (KeyError, TypeError, AttributeError) as exc:
                raise ValueError("invalid evidence timestamp") from exc
            return value

        result = verify_entry(
            entry,
            repository=repo,
            target_sha=sha,
            terminal=config["terminal_migration"],
            runs=runs,
            artifacts=artifacts,
            load_evidence=load,
        )
        result["source_sha"] = sha
        result["workflow"] = entry["workflow"]
        result["retained_artifacts"] = [
            {
                "id": a["id"],
                "name": a["name"],
                "expired": a.get("expired", False),
                "run_id": a.get("workflow_run", {}).get("id"),
            }
            for a in artifacts
            if a.get("name") == entry["artifact"]
        ]
        if result["workflow_run_id"]:
            run_id = result["workflow_run_id"]
            attempt = result["workflow_run_attempt"]
            jobs = api(f"repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100").get("jobs", [])
            for required in entry["required_jobs"]:
                selected = [j for j in jobs if j["name"] == required]
                if len(selected) != 1 or selected[0]["conclusion"] != "success":
                    result["errors"].append(f"mandatory job failed, missing, ambiguous or skipped: {required}")
            if result["errors"]:
                result["status"] = "fail"
        results.append(result)
    report = {
        "schema_version": "1.0",
        "repository": repo,
        "target_sha": sha,
        "results": results,
        "gate_0_status": "GATE_0_GREEN" if all(r["status"] == "pass" for r in results) else "GATE_0_BLOCKED",
        "release_decision": "NO_GO",
        "candidate_frozen": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["gate_0_status"])
    return 0 if report["gate_0_status"] == "GATE_0_GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
