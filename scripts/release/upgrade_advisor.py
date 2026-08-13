#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.current_terminal_migration import migration_report
from src.platform_lifecycle.compatibility import PlatformProfile, assess_upgrade, load_policy


def main() -> bool:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--evidence")
    args = parser.parse_args()
    matrix = load_policy()
    terminal = migration_report()["terminal_migration"]

    def profile(version: str) -> PlatformProfile:
        return PlatformProfile(
            version, "3.17.0", "1.30.0", "9.4.2", "3.13.0", "22.0.0", "dataobs-oidc-v1", "1.0.0", "1.0.0", "1", terminal
        )

    evidence = json.loads(Path(args.evidence).read_text()) if args.evidence else {}
    result = assess_upgrade(profile(matrix["dataobs_version"]), profile(args.target), evidence)
    print(
        json.dumps(
            {
                "current": matrix["dataobs_version"],
                "target": args.target,
                "readiness": result.state,
                "blockers": result.reason_codes,
                "warnings": [],
                "rollback_classification": result.rollback,
                "plan": result.plan,
            },
            indent=2,
        )
    )
    return result.state != "ready"


if __name__ == "__main__":
    raise SystemExit(main())
