"""Independently verify Stream 360 Core exact-commit evidence."""

import json
import subprocess
import sys

evidence = json.load(open(sys.argv[1], encoding="utf-8"))
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
assert evidence["final_sha"] == actual
assert evidence["elasticsearch_version"] == "9.4.2"
assert evidence["terminal_migration"] == "0021_lineage_analysis_explorer"
required = (
    "api_contract",
    "filters_and_cursor",
    "topic_360",
    "consumer_group_360",
    "playwright",
    "accessibility",
    "tenant_isolation",
)
assert all(evidence.get(item) is True for item in required)
assert evidence.get("junit_results")
