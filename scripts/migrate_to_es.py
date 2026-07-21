#!/usr/bin/env python3
"""
DataObs — Migrate in-memory snapshot to Elasticsearch.

Usage
-----
    python scripts/migrate_to_es.py --snapshot snapshot.json

The snapshot file is a JSON object with three optional keys::

    {
      "rules":   [ {<rule doc>}, ... ],
      "quality": [ {<quality result doc>}, ... ],
      "lineage": [ {<lineage node doc>}, ... ]
    }

Strategy
--------
- Zero-downtime: the API continues to serve from the in-memory store
  (``DATAOBS_STORE_BACKEND=memory``) while this script bulk-indexes to ES.
- After the script exits 0, set ``DATAOBS_STORE_BACKEND=elasticsearch``
  and restart the API.

Environment variables
---------------------
ELASTICSEARCH_URL       ES endpoint (default: http://localhost:9200)
ELASTICSEARCH_USER      ES username (default: elastic)
ELASTICSEARCH_PASSWORD  ES password (default: "")
DATAOBS_TENANT_ID       Target tenant (default: default)

Exit codes
----------
0 — success
1 — argument / connection error
2 — partial failure (some docs failed to index)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
)
logger = logging.getLogger("migrate_to_es")


def _es_client():
    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        logger.error("elasticsearch-py is not installed.  Run: pip install elasticsearch")
        sys.exit(1)

    url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    user = os.getenv("ELASTICSEARCH_USER", "elastic")
    password = os.getenv("ELASTICSEARCH_PASSWORD", "")
    es = Elasticsearch([url], basic_auth=(user, password), request_timeout=30)
    if not es.ping():
        logger.error("Cannot reach Elasticsearch at %s", url)
        sys.exit(1)
    return es


def _bulk_index(
    es,
    store,
    docs: List[Dict[str, Any]],
    doc_type: str,
) -> int:
    """Index *docs* into the store. Returns failure count."""
    failures = 0
    for doc in docs:
        try:
            if doc_type == "rules":
                store.save_rule(doc)
            elif doc_type == "quality":
                store.save_quality_result(doc)
            elif doc_type == "lineage":
                store.save_lineage_node(doc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to index %s doc %s: %s", doc_type, doc.get("id", "?"), exc)
            failures += 1
    return failures


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Migrate DataObs snapshot to Elasticsearch.")
    parser.add_argument(
        "--snapshot",
        required=True,
        help="Path to snapshot JSON file produced by the in-memory store.",
    )
    parser.add_argument(
        "--tenant",
        default=os.getenv("DATAOBS_TENANT_ID", "default"),
        help="Tenant ID (default: 'default').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the snapshot without writing to ES.",
    )
    args = parser.parse_args(argv)

    # ── Load snapshot ─────────────────────────────────────────────────────
    try:
        with open(args.snapshot) as fh:
            snapshot: Dict[str, Any] = json.load(fh)
    except FileNotFoundError:
        logger.error("Snapshot file not found: %s", args.snapshot)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in snapshot: %s", exc)
        sys.exit(1)

    rules = snapshot.get("rules", [])
    quality = snapshot.get("quality", [])
    lineage = snapshot.get("lineage", [])

    logger.info(
        "Snapshot loaded — rules: %d, quality results: %d, lineage nodes: %d",
        len(rules),
        len(quality),
        len(lineage),
    )

    if args.dry_run:
        logger.info("Dry-run mode — no data written.")
        sys.exit(0)

    # ── Connect & initialise store ────────────────────────────────────────
    es = _es_client()
    try:
        from src.api.es_store import ElasticsearchStore
    except ImportError:
        logger.error(
            "Cannot import ElasticsearchStore. Run from the repo root:\n"
            "    PYTHONPATH=. python scripts/migrate_to_es.py ..."
        )
        sys.exit(1)

    store = ElasticsearchStore(es, tenant_id=args.tenant)
    logger.info("Connected to ES.  Tenant: %s", args.tenant)

    # ── Migrate ───────────────────────────────────────────────────────────
    total_failures = 0

    if rules:
        logger.info("Migrating %d rules …", len(rules))
        total_failures += _bulk_index(es, store, rules, "rules")

    if quality:
        logger.info("Migrating %d quality results …", len(quality))
        total_failures += _bulk_index(es, store, quality, "quality")

    if lineage:
        logger.info("Migrating %d lineage nodes …", len(lineage))
        total_failures += _bulk_index(es, store, lineage, "lineage")

    # ── Summary ───────────────────────────────────────────────────────────
    total = len(rules) + len(quality) + len(lineage)
    succeeded = total - total_failures
    logger.info(
        "Migration complete — %d/%d documents indexed successfully.",
        succeeded,
        total,
    )

    if total_failures > 0:
        logger.warning("%d documents failed to index.", total_failures)
        sys.exit(2)

    logger.info(
        "\nNext steps:\n"
        "  1. Set DATAOBS_STORE_BACKEND=elasticsearch in your .env\n"
        "  2. Set DATAOBS_TENANT_ID=%s in your .env\n"
        "  3. Restart the API: docker compose restart dataobs-api",
        args.tenant,
    )


if __name__ == "__main__":
    main()
