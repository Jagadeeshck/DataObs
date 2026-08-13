#!/usr/bin/env python3
"""Bounded GitHub Actions posture checks; emits locations, never secret values."""

import argparse
import json
from pathlib import Path

import yaml


def inspect(paths):
    findings = []
    for path in paths:
        try:
            doc = yaml.safe_load(path.read_text()) or {}
        except Exception:
            findings.append({"file": str(path), "code": "INVALID_YAML", "severity": "high"})
            continue
        trigger = doc.get("on", doc.get(True, {}))
        perms = doc.get("permissions")
        if perms == "write-all":
            findings.append({"file": str(path), "code": "BROAD_WRITE_ALL", "severity": "high"})
        if isinstance(perms, dict) and any(
            v == "write" for k, v in perms.items() if k not in {"contents", "id-token", "packages", "attestations"}
        ):
            findings.append({"file": str(path), "code": "BROAD_WRITE_PERMISSION", "severity": "high"})
        if isinstance(trigger, dict) and "pull_request_target" in trigger:
            for name, job in (doc.get("jobs") or {}).items():
                if job.get("environment") or str(job).find("secrets.") >= 0:
                    findings.append(
                        {"file": str(path), "job": name, "code": "UNTRUSTED_PRIVILEGED_PR", "severity": "critical"}
                    )
        for name, job in (doc.get("jobs") or {}).items():
            if (
                isinstance(job, dict)
                and job.get("environment")
                and not any(x in str(trigger) for x in ("workflow_dispatch", "push", "workflow_call"))
            ):
                findings.append(
                    {"file": str(path), "job": name, "code": "UNSAFE_ENVIRONMENT_TRIGGER", "severity": "high"}
                )
    return findings


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--directory", type=Path, default=Path(".github/workflows"))
    p.add_argument("--output", type=Path, default=Path("workflow-security-report.json"))
    a = p.parse_args()
    f = inspect(sorted(a.directory.glob("*.y*ml")))
    r = {"schema_version": "1.0", "status": "review_required" if f else "pass", "finding_count": len(f), "findings": f}
    a.output.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print(r["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
