#!/usr/bin/env python3
"""Verify retained artifacts are bounded, relative and sentinel-free."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SENTINELS = (
    b"DATAOBS_CERT_SENTINEL_DB_PASSWORD",
    b"DATAOBS_CERT_SENTINEL_KAFKA_SECRET",
    b"DATAOBS_CERT_SENTINEL_WEBHOOK_TOKEN",
    b"DATAOBS_CERT_SENTINEL_API_KEY",
)

MAX_BYTES = 100 * 1024 * 1024
MANIFEST_NAMES = {"certification-evidence.json", "manifest.json"}
REQUIRED_FOUNDATION_CONTROLS = {
    "cross_tenant_state_isolation",
    "cross_environment_state_isolation",
    "same_operation_id_scope_isolation",
    "cross_tenant_plan_isolation",
    "cross_tenant_result_isolation",
    "cross_tenant_history_isolation",
    "wrong_scope_claim_denial",
    "wrong_scope_search_isolation",
}


def _security_errors(root: Path) -> list[str]:
    path = root / "security-report.json"
    if not path.is_file():
        return []
    report = json.loads(path.read_text())
    controls = report.get("controls", [])
    ids = [control.get("control_id") for control in controls if isinstance(control, dict)]
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("security controls are not unique")
    if set(ids) != REQUIRED_FOUNDATION_CONTROLS:
        errors.append("required foundation security control set is incomplete")
    if any(control.get("assertion_count", 0) <= 0 for control in controls if isinstance(control, dict)):
        errors.append("security control has zero assertions")
    passed = sum(control.get("passed") is True for control in controls if isinstance(control, dict))
    if report.get("scenario_count") != len(controls) or report.get("passed_count") != passed:
        errors.append("security control count mismatch")
    if report.get("failed_count") != 0 or report.get("result") != "passed":
        errors.append("security report did not pass")
    return errors


def verify(root: Path, *, sentinels_only: bool = False) -> list[str]:
    errors = []
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink is forbidden: {path.relative_to(root)}")
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if path.stat().st_size > MAX_BYTES:
            errors.append(f"artifact exceeds 100 MiB: {relative}")
        data = path.read_bytes()
        if any(value in data for value in SENTINELS):
            errors.append(f"sentinel remains: {relative}")
    if sentinels_only:
        return errors
    manifest_path = root / "certification-evidence.json"
    alias_path = root / "manifest.json"
    if not manifest_path.is_file():
        errors.append("certification-evidence.json is missing")
        return errors
    if not alias_path.is_file():
        errors.append("manifest.json alias is missing")
        return errors
    if alias_path.read_bytes() != manifest_path.read_bytes():
        errors.append("manifest.json alias is not byte-identical to certification-evidence.json")
    manifest = json.loads(manifest_path.read_text())
    errors.extend(_security_errors(root))
    listed = set()
    for artifact in manifest.get("artifacts", []):
        relative = Path(artifact["path"])
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"unsafe manifest path: {relative}")
            continue
        if relative.as_posix() in MANIFEST_NAMES:
            errors.append(f"manifest must not list itself or its alias: {relative}")
            continue
        listed.add(relative.as_posix())
        target = root / relative
        if not target.is_file():
            errors.append(f"listed artifact is missing: {relative}")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != artifact["sha256"]:
            errors.append(f"sha256 mismatch: {relative}")
    retained = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.relative_to(root).as_posix() not in MANIFEST_NAMES and p.name != ".gitkeep"
    }
    for relative in sorted(retained - listed):
        errors.append(f"retained artifact is not listed: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--sentinels-only", action="store_true")
    args = parser.parse_args()
    errors = verify(args.root.resolve(), sentinels_only=args.sentinels_only)
    if errors:
        print("\n".join(f"ERROR: {x}" for x in errors))
        return 1
    print("artifact verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
