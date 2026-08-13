"""Safe Asset Trust runtime operator commands."""

import argparse
import json

from packages.domain_model.asset_trust import DEFAULT_WEIGHTS


def parser():
    result = argparse.ArgumentParser(prog="python -m services.asset_trust.cli")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("evaluate-due").add_argument("--limit", type=int, default=100)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--asset-id", required=True)
    commands.add_parser("doctor")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "doctor":
        ok = abs(sum(DEFAULT_WEIGHTS.values()) - 1) < 1e-9
        print(json.dumps({"status": "healthy" if ok else "invalid", "calculation_version": "asset-trust-v1"}))
        return 0 if ok else 1
    # Runtime wiring is deployment-owned. These commands are intentionally read-only
    # until a configured repository/worker factory is supplied by the service host.
    print(json.dumps({"status": "not_configured", "command": args.command}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
