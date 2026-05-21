#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SO_PATH = Path("kibana/dataobs-poc-saved-objects.ndjson")
REQUIRED_DASHBOARDS = {
    "DataObs Road Safety Executive Overview",
    "Data Quality & Bad Data Detection",
    "Freshness / Volume / Schema Drift",
    "Lineage & Impact",
    "Spark Pipeline Performance",
}
REQUIRED_DATA_VIEWS = {
    "dataobs-quality",
    "dataobs-alerts",
    "dataobs-freshness",
    "dataobs-volume",
    "dataobs-schema",
    "dataobs-lineage",
    "dataobs-assets",
    "dataobs-spark-metrics",
    "dataobs-rs-*",
    "dataobs-test-data",
    "dataobs-spark-results",
    "traces-apm*",
    "metrics-apm*",
    "logs-apm*",
}


def main() -> int:
    rows = [json.loads(line) for line in SO_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    dashboards = [r for r in rows if r.get("type") == "dashboard"]
    data_views = [r for r in rows if r.get("type") == "index-pattern"]

    names = {d["attributes"]["title"] for d in dashboards}
    missing_dashboards = REQUIRED_DASHBOARDS - names
    if missing_dashboards:
        raise SystemExit(f"Missing dashboards: {sorted(missing_dashboards)}")

    for d in dashboards:
        panels = d.get("attributes", {}).get("panelsJSON", "[]")
        if panels == "[]":
            raise SystemExit(f"Dashboard has empty panelsJSON: {d.get('id')}")
        decoded = json.loads(panels)
        if not decoded:
            raise SystemExit(f"Dashboard has no panels: {d.get('id')}")

    view_titles = {v["attributes"]["title"] for v in data_views}
    missing_views = REQUIRED_DATA_VIEWS - view_titles
    if missing_views:
        raise SystemExit(f"Missing data views: {sorted(missing_views)}")

    print(f"Validated {len(rows)} saved objects, {len(dashboards)} dashboards, {len(data_views)} data views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
