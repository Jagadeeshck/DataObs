#!/usr/bin/env python3
"""Fail when a required SEV1/SEV2 operational reason lacks a complete runbook."""

import argparse
from pathlib import Path

import yaml

REQUIRED = {
    "ELASTICSEARCH_UNAVAILABLE",
    "ELASTICSEARCH_OVERLOAD",
    "AUTHENTICATION_FAILURE",
    "TELEMETRY_UNAVAILABLE",
    "MIGRATION_FAILURE",
    "BACKUP_FAILURE",
    "RESTORE_FAILURE",
    "KUBERNETES_SECURITY_FAILURE",
    "RELEASE_VERIFICATION_FAILURE",
    "WORKER_STALLED",
    "PRIVILEGED_ACCESS_FAILURE",
}


def validate(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text())
    covered = set()
    for item in data.get("runbooks", []):
        if set(item.get("severity_coverage", [])) & {"SEV1", "SEV2"} and all(
            item.get(k)
            for k in ("detection", "mitigation", "recovery", "verification", "escalation", "evidence_requirements")
        ):
            covered.update(item.get("reason_codes", []))
    return sorted(REQUIRED - covered)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("registry", type=Path, nargs="?", default=Path("docs/operations/runbook-registry.yaml"))
    a = p.parse_args()
    missing = validate(a.registry)
    if missing:
        raise SystemExit("missing critical runbook coverage: " + ", ".join(missing))
    print("critical runbook coverage: pass")


if __name__ == "__main__":
    main()
