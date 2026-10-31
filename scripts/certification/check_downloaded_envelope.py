#!/usr/bin/env python3
"""Apply existing canonical evidence verification to a downloaded artifact directory."""

import argparse
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.release.release_metadata import terminal_migration  # noqa: E402
from scripts.release.verify_beta_candidate import read_evidence_archive, validate_evidence  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--category", action="append", required=True)
    args = parser.parse_args()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in args.directory.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(args.directory))
    value = read_evidence_archive(buffer.getvalue(), require_inventory=True)
    entry = {
        "workflow": args.workflow,
        "evidence_schema_version": "1.0",
        "expected_elasticsearch_version": "9.5.5",
        "required_test_categories": args.category,
    }
    errors = validate_evidence(
        entry, value, args.sha, terminal_migration(), {"id": args.run, "run_attempt": args.attempt, "event": args.event}
    )
    if value.get("repository") != args.repository:
        errors.append("repository mismatch")
    if errors:
        raise SystemExit("; ".join(errors))
    print("canonical downloaded envelope and supporting checksums verified")


if __name__ == "__main__":
    main()
