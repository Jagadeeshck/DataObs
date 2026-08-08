"""CI entry point. Exit: 0 pass/advisory warning, 1 enforced fail, 2 error, 3 partial."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import evaluate
from .models import ChangeGatePolicy, GateMode
from .reporters import json_report, markdown_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dataobs-change-gate")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("evaluate")
    for name in ("base-manifest", "head-manifest"):
        cmd.add_argument(f"--{name}", required=True)
    cmd.add_argument("--run-results")
    cmd.add_argument("--profile")
    cmd.add_argument("--baseline-profile")
    cmd.add_argument("--project", required=True)
    cmd.add_argument("--repository", default="local")
    cmd.add_argument("--pr-id", default="local")
    cmd.add_argument("--base-sha", default="0" * 40)
    cmd.add_argument("--head-sha", default="1" * 40)
    cmd.add_argument("--tenant", default="ci")
    cmd.add_argument("--environment", default="ci")
    cmd.add_argument("--mode", choices=[x.value for x in GateMode], default="enforced")
    cmd.add_argument("--require-evidence", action="append", default=[])
    cmd.add_argument("--format", choices=("json", "markdown"), default="json")
    cmd.add_argument("--output")
    args = parser.parse_args(argv)
    try:

        def load(path):
            return json.loads(Path(path).read_text()) if path else None

        policy = ChangeGatePolicy(
            project_id=args.project,
            repository=args.repository,
            gate_mode=GateMode(args.mode),
            required_evidence=tuple(args.require_evidence),
        )
        result = evaluate(
            tenant_id=args.tenant,
            environment=args.environment,
            repository=args.repository,
            project_id=args.project,
            pr_id=args.pr_id,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            base_manifest=load(args.base_manifest),
            head_manifest=load(args.head_manifest),
            policy=policy,
            run_results=load(args.run_results),
            baseline_profile=load(args.baseline_profile),
            branch_profile=load(args.profile),
        )
        rendered = markdown_report(result) if args.format == "markdown" else json_report(result)
        if args.output:
            Path(args.output).write_text(rendered)
        else:
            print(rendered)
        return (
            3
            if result["status"] == "partial"
            else 1 if result["status"] == "failed" else 2 if result["status"] == "error" else 0
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
