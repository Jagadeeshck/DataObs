"""Independently verify Kafka Cluster 360 exact-commit evidence."""

import json
import subprocess
import sys

evidence = json.load(open(sys.argv[1], encoding="utf-8"))
assert evidence["final_sha"] == subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
assert evidence["elasticsearch_version"] == "9.4.2"
assert evidence["terminal_migration"] == "0021_lineage_analysis_explorer"
required = (
    "cluster_overview",
    "broker_result",
    "topic_result",
    "consumer_group_result",
    "connector_result",
    "health_aggregation",
    "cursor_result",
    "tenant_isolation",
    "playwright",
    "accessibility",
)
assert all(evidence.get(key) is True for key in required)
assert evidence.get("junit_results")
