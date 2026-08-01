from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from packages.elastic_store.client import make_client

from .repository import ElasticsearchPathwayRepository, replay_start
from .service import PathwayWorkerService


def main() -> int:
    from src.telemetry import init_telemetry

    init_telemetry()
    parser = argparse.ArgumentParser(prog="dataobs-pathway-worker")
    parser.add_argument("command", choices=["run", "process-once", "replay", "status"])
    parser.add_argument("--config", default=os.getenv("DATAOBS_PATHWAY_CONFIG", "config/pathway-worker.example.yaml"))
    parser.add_argument("--interval", type=float, default=10)
    parser.add_argument("--replay-minutes", type=int, default=15)
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text())
    repository = ElasticsearchPathwayRepository(
        make_client(), config["tenant_id"], config["environment"], config["source_streams"]
    )
    service = PathwayWorkerService(repository, late_arrival_seconds=config.get("late_arrival_window_seconds", 300))
    if args.command == "status":
        print(json.dumps(repository.status(), sort_keys=True))
        return 0
    if args.command == "process-once":
        print(json.dumps(service.process_once(), sort_keys=True))
        return 0
    if args.command == "replay":
        print(json.dumps(service.process_once(replay_since=replay_start(args.replay_minutes)), sort_keys=True))
        return 0
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        service.process_once()
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
