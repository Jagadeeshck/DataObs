#!/usr/bin/env python3
"""Create and verify a bounded Elasticsearch snapshot for DataObs aliases."""

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
from scripts.operations.snapshot_common import snapshot_resources  # noqa: E402


def backup(
    es: Elasticsearch,
    repository: str,
    snapshot: str,
    *,
    repository_location: str | None = None,
    register_repository: bool = False,
) -> dict:
    terminal = migrations()[-1].migration_id
    if not es.ping():
        raise RuntimeError("Elasticsearch is unavailable")
    status = es.get(index="dataobs-system-migrations-v1", id=terminal)
    if not status.get("found", True):
        raise RuntimeError(f"terminal migration {terminal} is not applied")
    if register_repository:
        if not repository_location:
            raise ValueError("--repository-location is required with --register-repository")
        es.snapshot.create_repository(
            name=repository,
            repository={"type": "fs", "settings": {"location": repository_location}},
        )
    es.snapshot.verify_repository(name=repository)
    response = es.snapshot.create(
        repository=repository,
        snapshot=snapshot,
        indices=",".join(snapshot_resources()),
        wait_for_completion=True,
        include_global_state=False,
    )
    state = response.get("snapshot", {}).get("state")
    report = {
        "schema_version": "1",
        "operation": "backup",
        "snapshot": snapshot,
        "repository": repository,
        "terminal_migration": terminal,
        "status": "pass" if state == "SUCCESS" else "fail",
        "redaction_status": "pass",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if state != "SUCCESS":
        raise RuntimeError("snapshot did not complete successfully")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--repository-location")
    p.add_argument("--register-repository", action="store_true")
    args = p.parse_args()
    report = backup(
        Elasticsearch(args.url, request_timeout=30),
        args.repository,
        args.snapshot,
        repository_location=args.repository_location,
        register_repository=args.register_repository,
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
