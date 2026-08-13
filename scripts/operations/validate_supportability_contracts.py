#!/usr/bin/env python3
"""Validate bounded supportability YAML contracts without claiming certification."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    files = [
        "platform-support-profile.yaml",
        "platform-severity-model.yaml",
        "platform-escalation-matrix.yaml",
        "known-issues.yaml",
        "runbook-registry.yaml",
        "platform-operational-readiness.yaml",
    ]
    docs = {n: yaml.safe_load((ROOT / "docs/operations" / n).read_text()) for n in files}
    allowed = {"supported", "unsupported", "unvalidated", "degraded", "blocked", "unknown"}
    for name, item in docs["platform-support-profile.yaml"]["dimensions"].items():
        assert item["state"] in allowed and all(
            k in item for k in ("evidence_source", "evidence_timestamp", "reason_code", "remediation_code")
        ), name
    assert set(docs["platform-severity-model.yaml"]["severities"]) == {"SEV1", "SEV2", "SEV3", "SEV4"}
    ids = set()
    for issue in docs["known-issues.yaml"]["issues"]:
        assert issue["severity"] in {"SEV1", "SEV2", "SEV3", "SEV4"}
        assert issue["state"] in {"open", "mitigated", "fixed", "withdrawn"}
        assert re.fullmatch(r"(\*|\d+\.\d+(?:\.\d+)?(?:\s*[-,]\s*\d+\.\d+(?:\.\d+)?)?)", issue["affected_versions"])
        assert issue["issue_id"] not in ids
        ids.add(issue["issue_id"])
    print("supportability contracts: pass")


if __name__ == "__main__":
    main()
