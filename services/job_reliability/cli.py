"""Operator entry point for the reliability worker.

Production composition supplies an Elasticsearch repository through the API
container.  This CLI intentionally refuses to silently fall back to memory.
"""

from __future__ import annotations

import argparse
import json
import os


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="job-reliability")
    commands = value.add_subparsers(dest="command", required=True)
    commands.add_parser("once")
    commands.add_parser("run")
    commands.add_parser("health")
    job = commands.add_parser("evaluate-job")
    job.add_argument("--job-id", required=True)
    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("--from", dest="from_timestamp", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "health":
        print(json.dumps({"state": "unavailable", "reason": "runtime_repository_not_composed"}))
        return 1
    if not os.getenv("DATAOBS_ELASTICSEARCH_URL"):
        parser().error("DATAOBS_ELASTICSEARCH_URL is required; memory fallback is forbidden")
    # Repository composition remains centralized in the application container.
    print(json.dumps({"command": args.command, "state": "accepted", "external_execution": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
