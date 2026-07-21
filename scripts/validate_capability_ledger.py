#!/usr/bin/env python3
"""Validate the evidence-led capability ledger and active product claims."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/product/capability-ledger.yaml"
STATES = {
    "validated",
    "functional_unvalidated",
    "foundation",
    "scaffold",
    "not_started",
    "deprecated",
    "optional_integration",
}
READINESS = {"blocked", "internal_alpha", "design_partner", "production_candidate"}
DIMS = {"passed", "failed", "defined_not_run", "not_applicable", "missing"}
PILLARS = ["platform", "data_pipeline", "data", "finops_cost", "business", "ai_agent"]
VDIMS = [
    "unit",
    "integration",
    "real_stack",
    "hosted_ci",
    "browser",
    "accessibility",
    "security",
    "scale",
    "upgrade",
    "release",
]
STALE = [
    "DataObs follows a 4-pillar model",
    "future DataObs Console",
    "DATAOBS_BACKEND=all as a normal product mode",
    "OpenSearch/Grafana as equal authoritative planes",
    "autonomous remediation enabled",
    "DataObs is production-ready",
]


def load(path: Path = LEDGER):
    return yaml.safe_load(path.read_text())


def validate(data: dict) -> list[str]:
    e = []
    caps = data.get("capabilities", [])
    ids = [c.get("id") for c in caps]
    if data.get("canonical_pillars") != PILLARS:
        e.append("canonical_pillars must use the six-pillar order")
    if len(ids) != len(set(ids)):
        e.append("duplicate capability IDs")
    openapi = json.loads((ROOT / "openapi.json").read_text()).get("paths", {})
    routes = (ROOT / "ui/dataobs-console/src/app/App.tsx").read_text()
    plan = json.loads(subprocess.check_output([sys.executable, "-m", "packages.elastic_store.cli", "plan"], cwd=ROOT))[
        "migrations"
    ]
    actual = {m["migration_id"]: m["checksum"] for m in plan}
    if data.get("migration_checksums") != actual:
        e.append("migration checksum immutability violation")
    for c in caps:
        cid = c.get("id", "<missing>")
        required = {
            "id",
            "name",
            "summary",
            "pillar",
            "domain",
            "state",
            "release_readiness",
            "implementation",
            "validation",
            "evidence",
            "blockers",
            "non_goals",
            "next_gate",
            "owner",
            "last_audited_at",
            "last_audited_commit",
        }
        if required - set(c):
            e.append(f"{cid}: missing fields {sorted(required-set(c))}")
        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", cid):
            e.append(f"{cid}: invalid ID")
        if c.get("state") not in STATES:
            e.append(f"{cid}: invalid state")
        if c.get("pillar") not in PILLARS:
            e.append(f"{cid}: invalid pillar")
        if c.get("release_readiness") not in READINESS:
            e.append(f"{cid}: invalid readiness")
        impl = c.get("implementation", {})
        ev = c.get("evidence", {})
        val = c.get("validation", {})
        for d in VDIMS:
            if val.get(d) not in DIMS:
                e.append(f"{cid}: invalid validation {d}")
        for p in impl.get("code_paths", []) + ev.get("tests", []) + ev.get("audit_docs", []) + ev.get("runbooks", []):
            if not (ROOT / p).exists():
                e.append(f"{cid}: missing path {p}")
        for api in impl.get("api_paths", []):
            if not api.startswith("planned:") and api not in openapi:
                e.append(f"{cid}: API absent from openapi.json: {api}")
        for route in impl.get("ui_routes", []):
            if not route.startswith("planned:") and route != "/" and f'path="{route.lstrip("/")}"' not in routes:
                e.append(f"{cid}: UI route absent: {route}")
        for mid in impl.get("migrations", []):
            if mid not in actual:
                e.append(f"{cid}: migration absent: {mid}")
        if c.get("state") == "validated" and any(val[d] in {"defined_not_run", "missing", "failed"} for d in VDIMS):
            e.append(f"{cid}: validated with incomplete evidence")
        if c.get("state") == "not_started" and any(impl.get(k) for k in impl):
            e.append(f"{cid}: not_started lists implemented surfaces")
        if c.get("state") == "optional_integration" and "Elasticsearch remains authoritative" not in c.get(
            "summary", ""
        ):
            e.append(f"{cid}: missing authoritative-plane disclaimer")
        if c.get("state") == "deprecated" and not c.get("deprecated_by"):
            e.append(f"{cid}: deprecated without replacement")
        if val.get("hosted_ci") == "passed" and not any(
            re.search(r"https?://|run[-_ ]?id", str(x), re.I) for x in ev.get("artifacts", [])
        ):
            e.append(f"{cid}: hosted pass lacks run reference")
    for doc in [ROOT / "README.md", ROOT / "docs/product/README.md", ROOT / "docs/product/roadmap-v1.md"]:
        if doc.exists():
            text = doc.read_text()
            for phrase in STALE:
                if phrase in text:
                    e.append(f"{doc.relative_to(ROOT)}: stale claim: {phrase}")
    return e


def main() -> int:
    errors = validate(load())
    if errors:
        print("\n".join(f"ERROR: {x}" for x in errors))
        return 1
    counts = {s: sum(c["state"] == s for c in load()["capabilities"]) for s in sorted(STATES)}
    report = ROOT / "capability-validation-report.json"
    report.write_text(json.dumps({"status": "passed", "counts": counts}, indent=2) + "\n")
    print(f"capability ledger valid: {sum(counts.values())} capabilities; migrations 0001-0012 immutable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
