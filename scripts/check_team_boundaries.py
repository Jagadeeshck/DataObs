#!/usr/bin/env python3
"""Validate delivery-foundation ownership and deterministic fixtures."""

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
required_docs = [
    "docs/development/team-ownership.md",
    "docs/development/shared-contract-rules.md",
    "docs/development/migration-ownership.md",
    "docs/development/certification-evidence-contract.md",
]
required_templates = [
    ".github/pull_request_template.md",
    *[f".github/ISSUE_TEMPLATE/{x}.yml" for x in ("feature", "bug", "contract-change", "certification")],
]
workflows = [
    ".github/workflows/reusable-backend-validation.yml",
    ".github/workflows/reusable-console-validation.yml",
    ".github/workflows/team-delivery-foundation.yml",
]
protected = [
    "packages/elastic_store/manifest.py",
    "packages/elastic_store/migrations/",
    "scripts/check_migration_immutability.py",
    "scripts/certification/",
    "src/security/",
    ".github/workflows/",
    "helm/",
    "deploy/",
    "ui/dataobs-console/src/api/transport.ts",
    "ui/dataobs-console/src/api/generated/",
    "docs/product/capability-ledger.yaml",
]
errors = []
for p in required_docs + required_templates + workflows:
    if not (ROOT / p).exists():
        errors.append(f"missing {p}")
ownership = (ROOT / required_docs[0]).read_text()
for team in range(6):
    if f"Team {team}" not in ownership:
        errors.append(f"Team {team} undocumented")
codeowners = (ROOT / ".github/CODEOWNERS").read_text()
for p in protected:
    if p not in codeowners:
        errors.append(f"CODEOWNERS missing {p}")
data = yaml.safe_load((ROOT / "tests/fixtures/manifest.yaml").read_text())
keys = {
    "name",
    "owner_team",
    "schema_version",
    "tenant_id",
    "environment",
    "purpose",
    "contains_sensitive_data",
    "used_by",
}
for i, item in enumerate(data.get("fixtures", [])):
    if keys - set(item):
        errors.append(f"fixture {i} missing {sorted(keys-set(item))}")
    if item.get("contains_sensitive_data") is not False:
        errors.append(f"fixture {i} must be non-sensitive")
# Compare migration registry path against the baseline when available.
base = "origin/main"
if (
    subprocess.run(
        ["git", "rev-parse", "--verify", base], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode
    == 0
):
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", base + "...HEAD", "--", "packages/elastic_store/manifest.py"],
        cwd=ROOT,
        text=True,
    ).strip()
    if changed:
        errors.append("migration manifest changed")
if errors:
    print("\n".join("ERROR: " + e for e in errors))
    sys.exit(1)
print(f"team boundaries valid; {len(data['fixtures'])} deterministic fixture contracts; no migration added")
