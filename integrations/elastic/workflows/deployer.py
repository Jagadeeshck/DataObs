from __future__ import annotations

import argparse
import json
from pathlib import Path

from .validator import validate_managed_definitions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dataobs workflows")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ["validate", "plan", "deploy", "status"]:
        sub.add_parser(cmd)
    run = sub.add_parser("run")
    run.add_argument("workflow_id")
    args = parser.parse_args(argv)
    pack = validate_managed_definitions()
    if args.cmd in {"validate", "plan", "status"}:
        print(json.dumps({"workflows": pack, "mode": args.cmd}, indent=2))
        return 0
    if args.cmd == "deploy":
        print(
            json.dumps(
                {"applied": pack, "note": "set KIBANA_URL and KIBANA_API_KEY to deploy via public APIs"}, indent=2
            )
        )
        return 0
    print(json.dumps({"status": "not_configured", "workflow_id": getattr(args, "workflow_id", None)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
