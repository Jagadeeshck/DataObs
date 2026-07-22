"""Independent, bounded Data Product reconciliation command."""

from __future__ import annotations

import argparse
import json
import os
import signal

from elasticsearch import Elasticsearch

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.reconciliation import DataProductOperationService, OperationReconciliationRegistry


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="dataobs data-products")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("reconcile", "reconcile-operation"):
        command = commands.add_parser(name)
        command.add_argument("--tenant", required=True)
        command.add_argument("--environment", required=True)
        command.add_argument("--worker-id", required=True)
        command.add_argument("--json", action="store_true")
        command.add_argument("--claim-ttl-seconds", type=int, default=30)
        command.add_argument("--max-attempts", type=int, default=5)
        if name == "reconcile":
            command.add_argument("--limit", type=int, default=100)
            command.add_argument("--operation-kind", choices=OperationReconciliationRegistry.REQUIRED_KINDS)
        else:
            command.add_argument("--operation-id", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = ElasticsearchDataProductRepository(
        Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    )
    interrupted = False

    def stop(_signum, _frame):
        nonlocal interrupted
        interrupted = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    service = DataProductOperationService(
        repository,
        worker_id=args.worker_id,
        claim_ttl_seconds=args.claim_ttl_seconds,
        max_attempts=args.max_attempts,
    )
    if interrupted:
        return 2
    if args.command == "reconcile":
        result = service.reconcile_batch(
            args.tenant, args.environment, limit=args.limit, operation_kind=args.operation_kind
        )
        failed = result["failed"]
        retry = result["retry"]
    else:
        outcome = service.reconcile_operation(args.tenant, args.environment, args.operation_id)
        result = {"operation_id": args.operation_id, "outcome": outcome}
        failed = int(outcome == "failed")
        retry = int(outcome == "retry")
    print(json.dumps(result, sort_keys=True) if args.json else result)
    # 0 terminal success, 2 retry-only/interrupted, 1 unrecoverable failure.
    return 1 if failed else 2 if retry else 0


if __name__ == "__main__":
    raise SystemExit(main())
