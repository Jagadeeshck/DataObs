"""CLI for the Command Center projector.

  python -m services.command_center.cli project --tenant acme-retail --environment production
  python -m services.command_center.cli run    # continuous loop over all tenant/env pairs

Reads ELASTICSEARCH_* env via the shared elastic_store client. Intended to run as a
lightweight worker in the stack so the Console estate view reflects live collection.
"""

from __future__ import annotations

import argparse
import logging
import time

from packages.elastic_store.client import make_client

from .projector import CommandCenterProjector

logger = logging.getLogger("dataobs.command_center")


def _scopes(es, explicit_tenant: str | None, explicit_env: str | None) -> list[tuple[str, str]]:
    """Resolve tenant/environment pairs to project. Explicit args win; else discover."""
    if explicit_tenant and explicit_env:
        return [(explicit_tenant, explicit_env)]
    # Discover distinct tenant/environment pairs from the incidents read-model.
    try:
        response = es.search(
            index="dataobs-incidents-v1-read",
            size=0,
            aggs={
                "tenants": {
                    "composite": {
                        "size": 100,
                        "sources": [
                            {"tenant": {"terms": {"field": "tenant_id"}}},
                            {"env": {"terms": {"field": "environment"}}},
                        ],
                    }
                }
            },
        )
        buckets = response.get("aggregations", {}).get("tenants", {}).get("buckets", [])
        pairs = [(b["key"]["tenant"], b["key"]["env"]) for b in buckets]
        return pairs or [("default", "production")]
    except Exception:
        return [("default", "production")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Command Center projector")
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("project", help="project a single tenant/environment once")
    one.add_argument("--tenant", required=True)
    one.add_argument("--environment", required=True)

    loop = sub.add_parser("run", help="continuously project all discovered scopes")
    loop.add_argument("--interval", type=int, default=30, help="seconds between cycles")
    loop.add_argument("--tenant", default=None)
    loop.add_argument("--environment", default=None)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    es = make_client()
    projector = CommandCenterProjector(es)

    if args.command == "project":
        summary = projector.project(args.tenant, args.environment)
        print(f"overall_health={summary['overall_health']} complete={summary['data_status']['complete']}")
        return

    # run loop
    while True:
        for tenant, environment in _scopes(es, args.tenant, args.environment):
            try:
                projector.project(tenant, environment)
            except Exception:
                logger.exception("projection cycle failed for %s/%s", tenant, environment)
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()
