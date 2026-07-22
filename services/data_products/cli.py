"""Independent, bounded Data Product reconciliation command."""

from __future__ import annotations

import argparse
import json
import os

from elasticsearch import Elasticsearch

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.reconciliation import DataProductOperationService


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="dataobs data-products")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("reconcile", "reconcile-operation"):
        command = commands.add_parser(name)
        command.add_argument("--tenant", required=True)
        command.add_argument("--environment", required=True)
        command.add_argument("--worker-id", required=True)
        command.add_argument("--json", action="store_true")
        if name == "reconcile":
            command.add_argument("--limit", type=int, default=100)
        else:
            command.add_argument("--operation-id", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = ElasticsearchDataProductRepository(
        Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    )
    service = DataProductOperationService(repository, worker_id=args.worker_id)
    if args.command == "reconcile":
        result = service.reconcile_batch(args.tenant, args.environment, limit=args.limit)
        failed = result["failed"]
    else:
        outcome = service.reconcile_operation(args.tenant, args.environment, args.operation_id)
        result = {"operation_id": args.operation_id, "outcome": outcome}
        failed = int(outcome == "failed")
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
