#!/usr/bin/env python3
"""Restore a named DataObs snapshot and verify terminal state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from snapshot_common import ElasticsearchSnapshotClient, SnapshotError, report, verify_cluster


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    client = ElasticsearchSnapshotClient(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    try:
        before = client.request("GET", f"/_snapshot/{args.repository}/{args.snapshot}")
        snapshots = before.get("snapshots", [])
        if len(snapshots) != 1 or snapshots[0].get("state") != "SUCCESS":
            raise SnapshotError("requested completed snapshot is not available")
        restored = client.request(
            "POST",
            f"/_snapshot/{args.repository}/{args.snapshot}/_restore?wait_for_completion=true",
            {"indices": "dataobs-*,logs-dataobs.*", "include_global_state": False},
        )
        if restored.get("snapshot", {}).get("shards", {}).get("failed", 0) != 0:
            raise SnapshotError("one or more snapshot shards failed to restore")
        version = verify_cluster(client)
        evidence = report(
            operation="restore", repository=args.repository, snapshot=args.snapshot, version=version, status="pass"
        )
    except SnapshotError as exc:
        evidence = {"status": "fail", "reason_code": str(exc), "redaction_status": "passed"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if evidence["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
