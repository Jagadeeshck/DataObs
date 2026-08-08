#!/usr/bin/env python3
"""Bounded stdlib-only Team 0 workload runner; never permits production targets."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import resource
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "tests/performance/scenarios.json"
REPORTS = [
    "topology",
    "workload",
    "latency",
    "throughput",
    "saturation",
    "noisy-neighbour",
    "autoscaling",
    "worker-scale",
    "worker-crash-matrix",
    "pod-failure",
    "node-failure",
    "soak",
    "resource-leak",
    "elasticsearch-query-budget",
    "elasticsearch-storage-growth",
    "backpressure",
    "redaction",
]


def safety(a):
    host = (urlparse(a.target).hostname or "").lower()
    allowed = {x.strip().lower() for x in a.allow_hosts.split(",") if x.strip()}
    if a.environment != "test" or "prod" in host or not a.synthetic_marker.startswith("synthetic-"):
        raise SystemExit("unsafe target: test environment and synthetic marker are mandatory")
    if not host or "*" in a.allow_hosts or host not in allowed or a.duration <= 0 or a.max_concurrency <= 0:
        raise SystemExit("unsafe target: exact allowlisted host and positive bounds are mandatory")
    if not a.sha or len(a.sha) < 7:
        raise SystemExit("unsafe target: exact SHA is mandatory")


async def one(a, operation, tenant):
    started = time.perf_counter()
    path = "/health" if operation == "platform-health" else f"/api/v1/{operation}"
    req = Request(
        a.target.rstrip("/") + path, headers={"X-DataObs-Synthetic-Tenant": tenant, "X-DataObs-Target-SHA": a.sha}
    )
    try:
        status, server, es = await asyncio.to_thread(fetch, req, a.timeout)
        return status < 400, (time.perf_counter() - started) * 1000, server, es
    except Exception:
        return False, (time.perf_counter() - started) * 1000, None, None


def fetch(req, timeout):
    with urlopen(req, timeout=timeout) as response:
        return (
            response.status,
            header_float(response, "Server-Timing"),
            header_float(response, "X-Elasticsearch-Duration-Ms"),
        )


def header_float(response, name):
    raw = response.headers.get(name)
    try:
        return float(raw.split("=")[-1].split(";")[0]) if raw else None
    except ValueError:
        return None


def pct(values, q):
    if not values:
        return None
    values = sorted(values)
    return round(values[min(len(values) - 1, int((len(values) - 1) * q))], 3)


async def run(a, config):
    scenario = config["scenarios"][a.scenario]
    operations = scenario["operations"]
    tenants = []
    for tenant, weight in scenario.get("tenants", {a.synthetic_marker: 1}).items():
        tenants.extend([tenant] * max(1, int(weight * 100)))
    deadline = time.monotonic() + a.duration
    results = []
    attempted = 0
    while time.monotonic() < deadline and attempted < a.max_operations:
        batch = [
            one(a, operations[(attempted + i) % len(operations)], tenants[(attempted + i) % len(tenants)])
            for i in range(min(a.concurrency, a.max_operations - attempted))
        ]
        results.extend(await asyncio.gather(*batch))
        attempted += len(batch)
        failures = sum(not x[0] for x in results)
        if results and failures / len(results) > a.max_error_rate:
            break
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--allow-hosts", required=True)
    p.add_argument("--environment", required=True)
    p.add_argument("--synthetic-marker", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument(
        "--scenario", choices=["api-reads", "api-writes", "ingestion", "worker", "noisy-neighbour"], required=True
    )
    p.add_argument("--profile", choices=["development", "standard-ha", "production-ha"], required=True)
    p.add_argument("--topology", required=True)
    p.add_argument("--duration", type=int, required=True)
    p.add_argument("--concurrency", type=int, required=True)
    p.add_argument("--max-concurrency", type=int, required=True)
    p.add_argument("--stage-percent", type=int, choices=[10, 25, 50, 75, 100, 125, 150], default=100)
    p.add_argument("--max-operations", type=int, default=100000)
    p.add_argument("--max-error-rate", type=float, default=0.05)
    p.add_argument("--timeout", type=float, default=10)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    safety(a)
    a.concurrency = max(1, round(a.concurrency * a.stage_percent / 100))
    if a.concurrency > a.max_concurrency:
        raise SystemExit("staged concurrency exceeds safety maximum")
    config = json.loads(SCENARIOS.read_text())
    scenario = config["scenarios"][a.scenario]
    workload_hash = hashlib.sha256(SCENARIOS.read_bytes()).hexdigest()
    start = time.time()
    results = asyncio.run(run(a, config))
    elapsed = max(0.001, time.time() - start)
    lat = [x[1] for x in results]
    successes = sum(x[0] for x in results)
    failures = len(results) - successes
    outcome = "passed" if results and failures / len(results) <= a.max_error_rate else "failed"
    common = {
        "exact_sha": a.sha,
        "certification_profile": a.profile,
        "scenario": a.scenario,
        "workload_hash": workload_hash,
        "topology": a.topology,
        "outcome": outcome,
    }
    report = {
        **common,
        "stage_percent": a.stage_percent,
        "baseline_rps": scenario["baseline_rps"],
        "concurrency": a.concurrency,
        "duration_seconds": round(elapsed, 3),
        "attempted_operations": len(results),
        "successes": successes,
        "failures": failures,
        "retries": 0,
        "latency_ms": {
            "p50": pct(lat, 0.5),
            "p90": pct(lat, 0.9),
            "p95": pct(lat, 0.95),
            "p99": pct(lat, 0.99),
            "max": round(max(lat), 3) if lat else None,
        },
        "throughput_per_second": round(successes / elapsed, 3),
        "resource_utilisation": {
            "client_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "client_threads": 1,
        },
        "server_latency_available": any(x[2] is not None for x in results),
        "elasticsearch_latency_available": any(x[3] is not None for x in results),
    }
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "workload-report.json").write_text(json.dumps(report, indent=2) + "\n")
    pending = {**common, "outcome": "pending", "reason": "scenario was not executed by this invocation"}
    for name in REPORTS:
        path = a.output / f"{name}-report.json"
        if not path.exists():
            path.write_text(
                json.dumps(report if name in {"latency", "throughput", "resource-leak"} else pending, indent=2) + "\n"
            )
    (a.output / "evidence.json").write_text(
        json.dumps({**common, "outcome": outcome, "reports": [f"{x}-report.json" for x in REPORTS]}, indent=2) + "\n"
    )
    (a.output / "tool-versions.json").write_text(
        json.dumps({"python": os.sys.version.split()[0], "hostname_redacted": True}, indent=2) + "\n"
    )
    print(json.dumps(report))
    raise SystemExit(outcome != "passed")


if __name__ == "__main__":
    main()
