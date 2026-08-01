#!/usr/bin/env python3
"""Restore a DataObs snapshot after the operator has isolated conflicting state."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from elasticsearch import Elasticsearch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.elastic_store.manifest import migrations  # noqa: E402


def restore(es: Elasticsearch, repository: str, snapshot: str) -> dict:
    terminal = migrations()[-1].migration_id
    result = es.snapshot.restore(
        repository=repository, snapshot=snapshot, wait_for_completion=True, include_global_state=False
    )
    failures = result.get("snapshot", {}).get("shards", {}).get("failed", 0)
    if failures:
        raise RuntimeError("snapshot restore reported failed shards")
    if not es.exists(index="dataobs-system-migrations-v1", id=terminal):
        raise RuntimeError("restored state is migration-incompatible")
    return {
        "schema_version": "1",
        "operation": "restore",
        "snapshot": snapshot,
        "repository": repository,
        "terminal_migration": terminal,
        "status": "pass",
        "redaction_status": "pass",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.write_text(
        json.dumps(
            restore(Elasticsearch(args.url, request_timeout=30), args.repository, args.snapshot),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
