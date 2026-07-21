#!/usr/bin/env python3
"""Resolve an event-aware, verified Git base for CI comparisons."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ZERO_SHA = "0" * 40


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git reference resolution failed")
    return result.stdout.strip()


def resolve(event: dict, event_name: str, explicit: str | None, main_ref: str) -> str:
    if explicit:
        candidate = explicit
    elif event_name == "pull_request":
        candidate = event.get("pull_request", {}).get("base", {}).get("sha")
    elif event_name == "push":
        candidate = event.get("before")
        if not candidate or candidate == ZERO_SHA:
            candidate = git("merge-base", "HEAD", main_ref)
    elif event_name == "workflow_dispatch":
        candidate = event.get("inputs", {}).get("base_ref") or git("merge-base", "HEAD", main_ref)
    else:
        candidate = git("merge-base", "HEAD", main_ref)
    if not candidate:
        raise ValueError(f"event {event_name!r} did not provide a base revision")
    return git("rev-parse", "--verify", f"{candidate}^{{commit}}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-file", type=Path, required=True)
    parser.add_argument("--event-name", default=os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch"))
    parser.add_argument("--base-ref")
    parser.add_argument("--main-ref", default="origin/main")
    args = parser.parse_args()
    try:
        event = json.loads(args.event_file.read_text())
        print(resolve(event, args.event_name, args.base_ref, args.main_ref))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: unable to resolve CI base: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
