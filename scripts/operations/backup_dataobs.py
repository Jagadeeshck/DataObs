#!/usr/bin/env python3
"""Create and verify a snapshot of Elasticsearch-backed DataObs state."""

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
    parser.add_argument("--repository-location", help="filesystem repository location; CI/test only")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    client = ElasticsearchSnapshotClient(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    try:
        version = verify_cluster(client)
        if args.repository_location:
            client.request(
                "PUT",
                f"/_snapshot/{args.repository}",
                {"type": "fs", "settings": {"location": args.repository_location, "compress": True}},
            )
        snapshot = client.request(
            "PUT",
            f"/_snapshot/{args.repository}/{args.snapshot}?wait_for_completion=true",
            {
                "indices": "dataobs-*,logs-dataobs.*",
                "ignore_unavailable": False,
                "include_global_state": False,
                "metadata": {"producer": "DataObs Team 6", "terminal_migration": "0021_lineage_analysis_explorer"},
            },
        )
        if snapshot.get("snapshot", {}).get("state") != "SUCCESS":
            raise SnapshotError("snapshot did not complete successfully")
        evidence = report(
            operation="backup", repository=args.repository, snapshot=args.snapshot, version=version, status="pass"
        )
    except SnapshotError as exc:
        evidence = {"status": "fail", "reason_code": str(exc), "redaction_status": "passed"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if evidence["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
