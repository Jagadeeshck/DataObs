"""Bounded worker entry point. Deployment and scheduling are owned by Team 0."""

from __future__ import annotations

import argparse
import json
import os
import signal
import time
from uuid import uuid4

from elasticsearch import Elasticsearch

from .elasticsearch_repository import OPERATION_READ, ElasticsearchAutomationRepository
from .execution import ExecutionWorker, ExecutorRegistry


def _repository() -> ElasticsearchAutomationRepository:
    endpoint = os.environ.get("ELASTICSEARCH_URL")
    if not endpoint:
        raise RuntimeError("ELASTICSEARCH_URL is required; process-local production state is forbidden")
    return ElasticsearchAutomationRepository(Elasticsearch(endpoint, request_timeout=10))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DataObs safe-remediation runtime")
    parser.add_argument("command", choices=("once", "worker", "health", "reconcile"))
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args(argv)
    repository = _repository()
    worker = ExecutionWorker(repository, ExecutorRegistry(), f"automation-{uuid4()}")
    if args.command == "health":
        response = repository.client.count(index=OPERATION_READ, query={"term": {"status": "queued"}})
        print(json.dumps({"status": "ok", "queued": int(response["count"])}))
        return 0
    if args.command == "reconcile":
        # V1 never guesses provider state. Operators must configure a certified lookup adapter first.
        print(json.dumps({"status": "safe_noop", "reason": "no_certified_executor_lookup"}))
        return 0
    if args.command == "once":
        print(json.dumps({"processed": worker.run_once(args.batch_size)}))
        return 0
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        processed = worker.run_once(args.batch_size)
        if not processed:
            time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
