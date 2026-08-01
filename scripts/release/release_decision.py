#!/usr/bin/env python3
"""Generate (never hand-edit) the fail-closed Team 0 release decision."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

STATES = {"NO_GO", "DRY_RUN_CERTIFIED", "APPROVED_FOR_PUBLICATION", "PUBLISHED", "VERIFICATION_FAILED"}
MANDATORY_RESULTS = (
    "deployment_certification_result",
    "security_certification_result",
    "tenant_isolation_result",
    "recovery_result",
    "upgrade_rollback_result",
    "independent_verification_result",
    "redaction_status",
    "vulnerability_policy_result",
)


def decide(manifest: dict[str, Any], *, dry_run: bool, publication_verified: bool = False) -> dict[str, Any]:
    failures = [key for key in MANDATORY_RESULTS if manifest.get(key) != "pass"]
    capabilities = manifest.get("capability_artifact_inventory")
    if not isinstance(capabilities, list) or any(
        x.get("mandatory", True) and x.get("status") != "pass" for x in capabilities
    ):
        failures.append("capability_artifact_inventory")
    if manifest.get("publication_status") == "published" and not publication_verified:
        state = "VERIFICATION_FAILED"
        failures.append("publication_verification")
    elif failures:
        state = "NO_GO"
    elif publication_verified and manifest.get("publication_status") == "published":
        state = "PUBLISHED"
    elif dry_run:
        state = "DRY_RUN_CERTIFIED"
    else:
        state = "APPROVED_FOR_PUBLICATION"
    assert state in STATES
    return {
        "schema_version": "1.0",
        "state": state,
        "go": state in {"APPROVED_FOR_PUBLICATION", "PUBLISHED"},
        "target_sha": manifest.get("target_sha"),
        "candidate_version": manifest.get("candidate_version"),
        "failed_checks": sorted(set(failures)),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "machine-evidence",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publication-verified", action="store_true")
    args = parser.parse_args()
    decision = decide(
        json.loads(args.manifest.read_text()), dry_run=args.dry_run, publication_verified=args.publication_verified
    )
    args.output.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")
    return 0 if decision["state"] != "VERIFICATION_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
