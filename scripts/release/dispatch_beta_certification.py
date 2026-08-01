#!/usr/bin/env python3
"""Dispatch and boundedly poll the mandatory Beta evidence workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path

import yaml

SHA = re.compile(r"^[0-9a-f]{40}$")


def gh(*args: str) -> object:
    result = subprocess.run(["gh", "api", *args], check=True, text=True, capture_output=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--target-sha", required=True)
    p.add_argument("--ref", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout-minutes", type=int, default=90)
    p.add_argument("--poll-seconds", type=int, default=15)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not SHA.fullmatch(a.target_sha):
        p.error("--target-sha must be an exact lowercase 40-character SHA")
    if not 1 <= a.poll_seconds <= 300 or not 1 <= a.timeout_minutes <= 1440:
        p.error("poll and timeout must be bounded")
    manifest = yaml.safe_load(a.manifest.read_text())
    if manifest["repository"] != a.repository:
        p.error("repository does not match manifest")
    workflows = sorted({e["workflow"] for e in manifest["capabilities"] if e["mandatory_for_beta"]})
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    report = {
        "schema_version": "1.1",
        "repository": a.repository,
        "target_sha": a.target_sha,
        "ref": a.ref,
        "dispatch_time": started,
        "dry_run": a.dry_run,
        "workflows": [],
        "status": "planned" if a.dry_run else "running",
    }
    if a.dry_run:
        report["workflows"] = [{"workflow": w, "inputs": {"target_sha": a.target_sha}} for w in workflows]
    else:
        branch = gh(f"repos/{a.repository}/git/ref/heads/{a.ref}")
        if branch["object"]["sha"] != a.target_sha:
            raise SystemExit("release ref does not point to target SHA")
        commit = gh(f"repos/{a.repository}/commits/{a.target_sha}")
        compare = gh(f"repos/{a.repository}/compare/{a.target_sha}...main")
        if not commit or compare.get("status") not in {"ahead", "identical"}:
            raise SystemExit("target SHA is not reachable from main")
        dispatch_epoch = time.time()
        for workflow in workflows:
            gh(
                "--method",
                "POST",
                f"repos/{a.repository}/actions/workflows/{workflow}/dispatches",
                "-f",
                f"ref={a.ref}",
                "-f",
                f"inputs[target_sha]={a.target_sha}",
            )
            report["workflows"].append(
                {
                    "workflow": workflow,
                    "dispatch_time": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "status": "queued",
                }
            )
        deadline = dispatch_epoch + a.timeout_minutes * 60
        pending = {x["workflow"]: x for x in report["workflows"]}
        while pending and time.time() < deadline:
            for workflow, item in list(pending.items()):
                runs = gh(
                    f"repos/{a.repository}/actions/workflows/{workflow}/runs?event=workflow_dispatch&head_sha={a.target_sha}&per_page=20"
                ).get("workflow_runs", [])
                runs = [
                    r
                    for r in runs
                    if dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).timestamp()
                    >= dispatch_epoch - 2
                ]
                if len(runs) > 1:
                    raise SystemExit(f"ambiguous workflow runs for {workflow}")
                if len(runs) == 1:
                    run = runs[0]
                    item.update(
                        {
                            "run_id": run["id"],
                            "run_attempt": run["run_attempt"],
                            "run_url": run["html_url"],
                            "status": run["status"],
                            "conclusion": run["conclusion"],
                        }
                    )
                    if run["status"] == "completed":
                        arts = gh(f"repos/{a.repository}/actions/runs/{run['id']}/artifacts").get("artifacts", [])
                        item["artifacts"] = [{"id": x["id"], "name": x["name"], "expired": x["expired"]} for x in arts]
                        pending.pop(workflow)
            if pending:
                time.sleep(a.poll_seconds)
        report["status"] = (
            "pass" if not pending and all(x.get("conclusion") == "success" for x in report["workflows"]) else "fail"
        )
        if pending:
            report["timeout_workflows"] = sorted(pending)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["status"] in {"planned", "pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
