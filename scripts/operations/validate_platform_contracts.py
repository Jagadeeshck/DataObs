#!/usr/bin/env python3
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    metrics = yaml.safe_load((ROOT / "docs/operations/platform-metrics.yaml").read_text())["metrics"]
    slos = yaml.safe_load((ROOT / "docs/operations/platform-slos.yaml").read_text())["slos"]
    alerts = yaml.safe_load((ROOT / "docs/operations/platform-alerts.yaml").read_text())["alerts"]
    names = [m["name"] for m in metrics]
    assert len(names) == len(set(names))
    assert all(m["unit"] in {"s", "By", "{request}", "{item}", "{exception}", "1"} for m in metrics)
    for m in metrics:
        bounds = m.get("boundaries", [])
        assert all(math.isfinite(x) for x in bounds) and bounds == sorted(set(bounds))
    slo_ids = {s["id"] for s in slos}
    alert_ids = {a["id"] for a in alerts}
    for m in metrics:
        assert set(m["slos"]) <= slo_ids and set(m["alerts"]) <= alert_ids
    for a in alerts:
        assert a["severity"] in {"info", "warning", "critical"}
        assert (ROOT / "docs/operations" / a["runbook"]).is_file()
    print(f"validated {len(metrics)} metrics, {len(slos)} SLOs, {len(alerts)} alerts")


if __name__ == "__main__":
    main()
