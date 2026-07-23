from __future__ import annotations

import argparse
import json

from .client import make_client
from .registry import apply, plan, rollback, status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dataobs elastic")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--through", dest="through_migration_id")
    sub.add_parser("status")
    rb = sub.add_parser("rollback")
    rb.add_argument("migration_id", nargs="?", default="0001_product_foundation")
    args = parser.parse_args(argv)
    if args.cmd == "plan":
        print(json.dumps({"migrations": plan()}, indent=2))
        return 0
    es = make_client()
    if args.cmd == "apply":
        print(json.dumps({"applied": apply(es, through_migration_id=args.through_migration_id)}, indent=2))
        return 0
    if args.cmd == "status":
        print(json.dumps(status(es), indent=2, default=str))
        return 0
    print(json.dumps(rollback(es, args.migration_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
