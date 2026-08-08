"""Bounded worker entry point. Deployment and scheduling are owned by Team 0."""

from __future__ import annotations

import argparse
import json
import os
import signal
import time
from uuid import uuid4

from elasticsearch import Elasticsearch

from .elasticsearch_repository import APPROVAL_READ, OPERATION_READ, ElasticsearchAutomationRepository
from .execution import ExecutionWorker, ExecutorRegistry
from .reconciliation import AutomationReconciler


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

        def count(index: str, query: dict[str, object]) -> int:
            return int(repository.client.count(index=index, query=query)["count"])

        print(
            json.dumps(
                {
                    "status": "ok",
                    "queued": count(OPERATION_READ, {"term": {"status": "queued"}}),
                    "reserved_approvals": count(APPROVAL_READ, {"term": {"approval_state": "reserved"}}),
                    "reconciliation_required": count(OPERATION_READ, {"term": {"status": "reconciliation_required"}}),
                    "pending_evidence": count(OPERATION_READ, {"term": {"metadata.transition_event_pending": True}}),
                }
            )
        )
        return 0
    if args.command == "reconcile":
        approvals = AutomationReconciler(repository).run_once(args.batch_size)
        executions = worker.recover_expired(args.batch_size)
        print(json.dumps({"status": "ok", "approvals_repaired": approvals, "executions_recovered": executions}))
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
