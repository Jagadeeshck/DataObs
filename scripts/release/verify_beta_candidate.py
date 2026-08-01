#!/usr/bin/env python3
"""Verify unambiguous, exact-commit Beta capability evidence."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

SHA = re.compile(r"^[0-9a-f]{40}$")
SUPPORTED_EVIDENCE_SCHEMAS = {"1.0"}


def _get_json(url: str, token: str) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError("GitHub returned a non-object response")
    return value


def _download_evidence(url: str, token: str) -> Mapping[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        archive = zipfile.ZipFile(io.BytesIO(response.read(50_000_001)))
    candidates = [name for name in archive.namelist() if name.endswith(("evidence.json", "audit.json"))]
    if len(candidates) != 1:
        raise ValueError("artifact must contain exactly one evidence.json or audit.json envelope")
    value = json.loads(archive.read(candidates[0]))
    if not isinstance(value, dict):
        raise ValueError("evidence envelope is not an object")
    return value


def validate_evidence(
    entry: Mapping[str, Any], evidence: Mapping[str, Any], target_sha: str, terminal: str
) -> list[str]:
    errors: list[str] = []
    schema = str(evidence.get("schema_version", evidence.get("evidence_schema_version", "")))
    if schema != str(entry["evidence_schema_version"]) or schema not in SUPPORTED_EVIDENCE_SCHEMAS:
        errors.append("unsupported evidence schema")
    producer = evidence.get("producer_sha", evidence.get("commit_sha", evidence.get("final_sha")))
    if producer != target_sha:
        errors.append("evidence producer SHA mismatch")
    if evidence.get("terminal_migration") != terminal:
        errors.append("terminal migration mismatch")
    version = evidence.get("elasticsearch_version", evidence.get("Elasticsearch_version"))
    if version != entry.get("expected_elasticsearch_version"):
        errors.append("Elasticsearch version mismatch")
    summaries = evidence.get("test_summaries", evidence.get("junit_summaries"))
    if not isinstance(summaries, list) or not summaries:
        errors.append("JUnit or equivalent test summary is missing")
    if not isinstance(evidence.get("tool_versions"), dict):
        errors.append("tool version metadata is missing")
    return errors


def verify_entry(
    entry: Mapping[str, Any],
    *,
    repository: str,
    target_sha: str,
    terminal: str,
    runs: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    load_evidence: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    expected_workflow = entry["workflow"]
    candidates = [
        run
        for run in runs
        if run.get("head_sha") == target_sha
        and run.get("status") == "completed"
        and run.get("event") == "workflow_dispatch"
        and run.get("path", "").endswith(str(expected_workflow))
        and run.get("repository", {}).get("full_name") == repository
    ]
    errors: list[str] = []
    if len(candidates) != 1:
        errors.append("missing qualifying workflow run" if not candidates else "multiple ambiguous workflow runs")
    elif candidates[0].get("conclusion") != entry["required_conclusion"]:
        errors.append(f"workflow conclusion is {candidates[0].get('conclusion')}")
    matching_artifacts: list[Mapping[str, Any]] = []
    if len(candidates) == 1:
        run_id = candidates[0].get("id")
        matching_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.get("workflow_run", {}).get("id") == run_id
            and artifact.get("name") == entry["artifact"]
            and not artifact.get("expired", False)
        ]
        if len(matching_artifacts) != 1:
            errors.append("required artifact is missing or ambiguous")
    if len(matching_artifacts) == 1:
        try:
            errors.extend(validate_evidence(entry, load_evidence(matching_artifacts[0]), target_sha, terminal))
        except (ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
            errors.append("invalid evidence JSON")
    mandatory = bool(entry["mandatory_for_beta"])
    status = "pass" if not errors else ("fail" if mandatory else "pending")
    return {
        "capability_id": entry["capability_id"],
        "owning_team": entry["owning_team"],
        "mandatory": mandatory,
        "status": status,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not SHA.fullmatch(args.target_sha):
        parser.error("--target-sha must be an exact lowercase 40-character commit SHA")
    token = os.getenv("GH_TOKEN")
    if not token:
        parser.error("GH_TOKEN is required")
    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("repository") != args.repository:
        parser.error("repository does not match certification manifest")
    results = []
    for entry in manifest["capabilities"]:
        workflow = urllib.parse.quote(str(entry["workflow"]), safe="")
        base = f"https://api.github.com/repos/{args.repository}"
        runs = _get_json(
            f"{base}/actions/workflows/{workflow}/runs?head_sha={args.target_sha}&per_page=100", token
        ).get("workflow_runs", [])
        artifacts = _get_json(
            f"{base}/actions/artifacts?name={urllib.parse.quote(str(entry['artifact']))}&per_page=100", token
        ).get("artifacts", [])
        results.append(
            verify_entry(
                entry,
                repository=args.repository,
                target_sha=args.target_sha,
                terminal=manifest["terminal_migration"],
                runs=runs,
                artifacts=artifacts,
                load_evidence=lambda artifact: _download_evidence(artifact["archive_download_url"], token),
            )
        )
    report = {"schema_version": "1.0", "target_sha": args.target_sha, "results": results}
    report["status"] = "pass" if all(r["status"] == "pass" or not r["mandatory"] for r in results) else "fail"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
