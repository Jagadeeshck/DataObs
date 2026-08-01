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
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

SHA = re.compile(r"^[0-9a-f]{40}$")
SUPPORTED_EVIDENCE_SCHEMAS = {"1.0", "1.1"}


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
        payload = response.read(50_000_001)
        if len(payload) > 50_000_000:
            raise ValueError("artifact archive exceeds 50 MB limit")
        archive = zipfile.ZipFile(io.BytesIO(payload))
    for info in archive.infolist():
        path = Path(info.filename)
        if path.is_absolute() or ".." in path.parts or info.file_size > 25_000_000:
            raise ValueError("artifact contains an unsafe archive path or member")
    candidates = [name for name in archive.namelist() if Path(name).name == "evidence.json"]
    if len(candidates) != 1:
        raise ValueError("artifact must contain exactly one evidence.json envelope")
    value = json.loads(archive.read(candidates[0]))
    if not isinstance(value, dict):
        raise ValueError("evidence envelope is not an object")
    return value


def validate_evidence(
    entry: Mapping[str, Any], evidence: Mapping[str, Any], target_sha: str, terminal: str,
    run: Mapping[str, Any] | None = None,
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
<<<<<<< HEAD
    if evidence.get("workflow_file") != entry.get("workflow"):
        errors.append("workflow file mismatch")
    if run is not None:
        if str(evidence.get("workflow_run_id")) != str(run.get("id")):
            errors.append("workflow run ID mismatch")
        if str(evidence.get("workflow_run_attempt")) != str(run.get("run_attempt", 1)):
            errors.append("workflow run attempt mismatch")
        if evidence.get("event") != run.get("event"):
            errors.append("workflow event mismatch")
    if evidence.get("redaction_status") != "pass":
        errors.append("redaction status is not pass")
    if evidence.get("status") != "pass":
        errors.append("overall evidence status is not pass")
    categories = {item.get("category") for item in summaries if isinstance(item, dict)} if isinstance(summaries, list) else set()
    missing = set(entry.get("required_test_categories", ())) - categories
    if missing:
        errors.append("required test categories are missing")
=======
    if schema == "1.1":
        if evidence.get("status") != "pass":
            errors.append("mandatory evidence status is not pass")
        if evidence.get("repository") != entry.get("repository", evidence.get("repository")):
            errors.append("evidence repository mismatch")
        if evidence.get("event") != "workflow_dispatch":
            errors.append("evidence event is not workflow_dispatch")
        if not isinstance(evidence.get("migration_count"), int) or evidence["migration_count"] < 1:
            errors.append("migration count is missing")
        if evidence.get("redaction_status") not in {"pass", "passed"}:
            errors.append("redaction status is not pass")
        if evidence.get("independent_verification_result") not in {"pass", "passed"}:
            errors.append("independent verification is not pass")
        skipped = evidence.get("skipped_test_summary", [])
        if skipped not in ([], {}, None, {"count": 0}):
            errors.append("mandatory evidence contains skipped tests")
        categories = {x.get("category") for x in summaries if isinstance(x, dict)}
        missing = set(entry.get("required_test_categories", [])) - categories
        if missing:
            errors.append("mandatory test categories are missing")
>>>>>>> origin/main
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
    accepted_events = set(entry.get("accepted_events", ["workflow_dispatch"]))
    candidates = [
        run
        for run in runs
        if run.get("head_sha") == target_sha
        and run.get("status") == "completed"
        and run.get("event") in accepted_events
        and run.get("path", "").endswith(str(expected_workflow))
        and run.get("repository", {}).get("full_name") == repository
    ]
    errors: list[str] = []
    selected: Mapping[str, Any] | None = None
    if not candidates:
        errors.append("missing qualifying workflow run")
    else:
        # A rerun supersedes earlier attempts of the same run. Distinct successful
        # run IDs remain ambiguous because neither can be silently preferred.
        latest_by_id: dict[Any, Mapping[str, Any]] = {}
        for item in candidates:
            key = item.get("id")
            if int(item.get("run_attempt", 1)) >= int(latest_by_id.get(key, {}).get("run_attempt", 0)):
                latest_by_id[key] = item
        successful = [item for item in latest_by_id.values() if item.get("conclusion") == entry["required_conclusion"]]
        if len(successful) == 1:
            selected = successful[0]
        elif len(successful) > 1:
            errors.append("multiple ambiguous workflow runs")
        else:
            selected = max(latest_by_id.values(), key=lambda item: int(item.get("run_attempt", 1)))
            errors.append(f"workflow conclusion is {selected.get('conclusion')}")
    matching_artifacts: list[Mapping[str, Any]] = []
    evidence: Mapping[str, Any] = {}
    if selected is not None and not errors:
        run_id = selected.get("id")
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
<<<<<<< HEAD
            evidence = load_evidence(matching_artifacts[0])
            errors.extend(validate_evidence(entry, evidence, target_sha, terminal, selected))
=======
            payload = load_evidence(matching_artifacts[0])
            enriched = dict(entry)
            enriched["repository"] = repository
            errors.extend(validate_evidence(enriched, payload, target_sha, terminal))
            run = candidates[0]
            if payload.get("workflow_path") not in (None, run.get("path")):
                errors.append("evidence workflow path mismatch")
            if payload.get("workflow_run_attempt") not in (None, run.get("run_attempt")):
                errors.append("workflow attempt mismatch")
            if run.get("run_started_at") and payload.get("generated_at"):
                if datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00")) < datetime.fromisoformat(
                    run["run_started_at"].replace("Z", "+00:00")
                ):
                    errors.append("evidence predates workflow start")
            for item in payload.get("artifact_inventory", []):
                if isinstance(item, dict) and "sha256" in item and not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
                    errors.append("invalid artifact file hash")
>>>>>>> origin/main
        except (ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
            errors.append("invalid evidence JSON")
    mandatory = bool(entry["mandatory_for_beta"])
    status = "pass" if not errors else ("fail" if mandatory else "optional_failed")
    return {
        "capability_id": entry["capability_id"],
        "owning_team": entry["owning_team"],
        "mandatory": mandatory,
        "status": status,
        "errors": errors,
        "reason_codes": [error.lower().replace(" ", "_") for error in errors],
        "workflow_run_id": selected.get("id") if selected else None,
        "workflow_run_attempt": selected.get("run_attempt", 1) if selected else None,
        "workflow_run_url": selected.get("html_url") if selected else None,
        "artifact_id": matching_artifacts[0].get("id") if len(matching_artifacts) == 1 else None,
        "artifact_name": matching_artifacts[0].get("name") if len(matching_artifacts) == 1 else None,
        "evidence_producer_sha": evidence.get("producer_sha"),
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
    report = {"schema_version": "1.0", "repository": args.repository, "target_sha": args.target_sha, "results": results}
    report["status"] = "pass" if all(r["status"] == "pass" or not r["mandatory"] for r in results) else "fail"
    report["release_decision"] = "assemble" if report["status"] == "pass" else "block"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
