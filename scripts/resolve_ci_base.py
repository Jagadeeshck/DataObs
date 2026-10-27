#!/usr/bin/env python3
"""Resolve an event-aware, verified Git base for immutable-history checks."""

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


def verified_commit(candidate: str, label: str) -> str:
    try:
        return git("rev-parse", "--verify", f"{candidate}^{{commit}}")
    except ValueError as exc:
        raise ValueError(f"{label} {candidate!r} is unavailable; checkout full history (fetch-depth: 0)") from exc


def first_parent() -> str:
    parents = git("rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parents) < 2:
        raise ValueError("HEAD is a root commit and has no comparison base")
    return parents[1]


def resolve(
    event: dict,
    event_name: str,
    explicit: str | None,
    main_ref: str,
    *,
    bootstrap: bool = False,
) -> str:
    """Return a reachable base commit, failing closed on ambiguity or missing history."""
    candidate: str | None
    if explicit:
        candidate, source = explicit, "explicit base"
    elif event_name == "pull_request":
        raw_candidate = event.get("pull_request", {}).get("base", {}).get("sha")
        candidate = str(raw_candidate) if raw_candidate else None
        source = "pull request base SHA"
    elif event_name == "push":
        raw_candidate = event.get("before")
        candidate = str(raw_candidate) if raw_candidate else None
        source = "push before SHA"
        if not candidate or candidate == ZERO_SHA:
            if bootstrap:
                return verified_commit("HEAD", "bootstrap HEAD")
            candidate, source = first_parent(), "verified first parent"
    elif event_name == "workflow_dispatch":
        raw_candidate = event.get("inputs", {}).get("base_ref")
        candidate = str(raw_candidate) if raw_candidate else None
        source = "workflow_dispatch base_ref"
        if not candidate:
            try:
                candidate = git("merge-base", "HEAD", main_ref)
                source = f"merge base with {main_ref}"
            except ValueError:
                candidate, source = first_parent(), "verified first parent"
            if candidate == verified_commit("HEAD", "HEAD"):
                candidate, source = first_parent(), "verified first parent"
    else:
        raise ValueError(f"unsupported GitHub event {event_name!r}")

    if not candidate:
        raise ValueError(f"{source} is missing")
    base = verified_commit(str(candidate), source)
    head = verified_commit("HEAD", "HEAD")
    if base == head and not bootstrap:
        raise ValueError("comparison base resolves to HEAD; refusing a vacuous immutability check")
    try:
        git("merge-base", "--is-ancestor", base, head)
    except ValueError as exc:
        raise ValueError(f"resolved base {base} is not an ancestor of HEAD") from exc
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--event-file",
        type=Path,
        default=Path(os.environ.get("GITHUB_EVENT_PATH", "")) if os.environ.get("GITHUB_EVENT_PATH") else None,
    )
    parser.add_argument("--event-name", default=os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch"))
    parser.add_argument("--base-ref")
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--bootstrap", action="store_true", help="permit HEAD only for an authorized root bootstrap")
    args = parser.parse_args()
    try:
        event = json.loads(args.event_file.read_text()) if args.event_file else {}
        print(resolve(event, args.event_name, args.base_ref, args.main_ref, bootstrap=args.bootstrap))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: unable to resolve CI base: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
