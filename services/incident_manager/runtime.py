"""Bounded incident-correlation reconciliation command.

Production invokes this module with Elasticsearch configuration. Deployment packaging
is intentionally a Team 0 handoff.
"""

from __future__ import annotations

import argparse
import json
import signal
import time
from threading import Event

from src.api.app import create_app

MAX_BATCH = 100


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("once", "worker", "reconcile", "health"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args()
    app = create_app()
    coordinator = app.state.incident_correlation_coordinator
    if args.command == "health":
        backlog = len(coordinator.correlations.list_deferred(limit=MAX_BATCH))
        print(json.dumps({"status": "ok", "backlog": backlog, "maximum_batch": MAX_BATCH}))
        return 0
    batch = min(max(args.batch_size, 1), MAX_BATCH)
    if args.command in {"once", "reconcile"}:
        print(json.dumps(coordinator.reconcile(limit=batch), sort_keys=True))
        return 0
    stopped = Event()
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, lambda *_: stopped.set())
    while not stopped.is_set():
        result = coordinator.reconcile(limit=batch)
        if not result["completed"]:
            stopped.wait(min(max(args.poll_seconds, 0.25), 60.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
