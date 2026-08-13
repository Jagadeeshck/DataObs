#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import yaml

from scripts.release.current_terminal_migration import migration_report

ROOT = Path(__file__).resolve().parents[2]


def main():
    expected = migration_report()["terminal_migration"]
    errors = []
    for name in ("values.yaml", "values-production.yaml"):
        actual = yaml.safe_load((ROOT / "helm/dataobs" / name).read_text())["migrationJob"]["terminalMigration"]
        if actual != expected:
            errors.append(f"{name}: {actual} != {expected}")
    print("\n".join(errors) if errors else f"Helm terminal migration synchronized: {expected}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
