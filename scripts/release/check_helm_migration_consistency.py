#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import yaml  # type: ignore[import-untyped]

from scripts.release.current_terminal_migration import migration_report

ROOT = Path(__file__).resolve().parents[2]


def main():
    expected = migration_report()["terminal_migration"]
    errors = []
    for name in ("values.yaml", "values-production.yaml"):
        actual = yaml.safe_load((ROOT / "helm/dataobs" / name).read_text())["migrationJob"]["terminalMigration"]
        if actual != expected:
            errors.append(f"{name}: {actual} != {expected}")
    values_schema = json.loads((ROOT / "helm/dataobs/values.schema.json").read_text())
    schema_terminal = values_schema["properties"]["migrationJob"]["properties"]["terminalMigration"].get("const")
    if schema_terminal != expected:
        errors.append(f"values.schema.json: {schema_terminal} != {expected}")
    release_schema = json.loads((ROOT / "docs/release/dataobs-release-manifest.schema.json").read_text())
    release_terminal = release_schema["properties"]["terminal_migration"].get("const")
    if release_terminal != expected:
        errors.append(f"dataobs-release-manifest.schema.json: {release_terminal} != {expected}")
    release_example = json.loads((ROOT / "docs/release/dataobs-release-manifest.example.json").read_text())
    if release_example.get("terminal_migration") != expected:
        errors.append(
            "dataobs-release-manifest.example.json: " f"{release_example.get('terminal_migration')} != {expected}"
        )
    print("\n".join(errors) if errors else f"Helm terminal migration synchronized: {expected}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
