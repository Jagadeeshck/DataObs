#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate_static() -> None:
    schema = json.loads((ROOT / "config/platform/environments.schema.json").read_text())
    assert schema["additionalProperties"] is False
    for name in ("platform-ha-profiles.yaml", "platform-capacity-profiles.yaml"):
        data = yaml.safe_load((ROOT / "docs/operations" / name).read_text()); assert data["schema_version"] == "1"
    required = ["environment-provisioning", "environment-upgrade", "environment-rollback", "cluster-registration",
        "tenant-onboarding", "tenant-suspension", "tenant-offboarding", "release-promotion", "deployment-drift",
        "release-skew", "platform-failover", "ha-failure-domain"]
    for name in required:
        text = (ROOT / "docs/operations" / f"{name}.md").read_text()
        for section in ("Preconditions", "Permissions and approval", "Plan and execution", "Verification", "Rollback", "Evidence and escalation", "Prohibited actions"):
            assert f"## {section}" in text, (name, section)


def validate_terraform() -> None:
    workflow = (ROOT / ".github/workflows/team-0-infrastructure-validation-v1.yml").read_text()
    assert not re.search(r"terraform\s+apply", workflow)
    canonical = "\n".join(p.read_text() for p in (ROOT / "infra/terraform/platform").glob("*.tf"))
    assert "aws_opensearch_domain" not in canonical
    assert not re.search(r'(?i)(password|api_key|private_key)\s*=\s*"[^$]', canonical)
    assert 'Action = "*"' not in canonical and 'actions = ["*"]' not in canonical


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--all", action="store_true"); parser.add_argument("--terraform", action="store_true"); args=parser.parse_args()
    if args.all: validate_static(); validate_terraform()
    elif args.terraform: validate_terraform()
    else: validate_static()
