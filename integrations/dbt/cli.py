#!/usr/bin/env python3
"""DataObs dbt ingestion CLI (Team 4 — Integration SDK / packaging).

Thin, dependency-light driver that loads dbt Core artifacts from disk, previews
them with the *existing* version-aware parsers under ``integrations/dbt/artifacts``
(never emitting raw/compiled SQL — only one-way fingerprints), and drives the
canonical ingestion endpoint ``POST /api/v1/dbt/artifacts`` owned by Team 2.

This module adds packaging only. It does not re-implement parsing, mapping, or
the HTTP contract, and it must not be used to claim a connector is "supported" or
"healthy" — it merely forwards artifacts a caller already produced with dbt.

Usage::

    dataobs dbt ingest \
        --api-url https://dataobs.example/api \
        --token-env DATAOBS_TOKEN \
        --project-id my_project \
        --project-name "My Project" \
        --manifest target/manifest.json \
        --run-results target/run_results.json

Tenant and environment are resolved server-side from the bearer token; the CLI
never sets them. Secrets are read from the environment, never from flags.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from integrations.dbt.artifacts import manifest as manifest_parser
from integrations.dbt.artifacts import run_results as run_results_parser

# Ordered so dependency graph (manifest) is ingested before run outcomes.
_ARTIFACT_ORDER: tuple[str, ...] = ("manifest", "run_results", "catalog", "freshness")

# Local preview parsers, by artifact_type. Reuse of existing parsers only.
_PREVIEW: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "manifest": manifest_parser.parse,
    "run_results": run_results_parser.parse,
}


class CliError(Exception):
    """Operator-facing error with a safe, non-sensitive message."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text()
    except OSError as exc:
        raise CliError(f"cannot read artifact {path}: {exc.strerror or exc}") from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"artifact {path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(document, dict):
        raise CliError(f"artifact {path} must be a JSON object, got {type(document).__name__}")
    return document


def preview(artifact_type: str, document: dict[str, Any]) -> dict[str, Any]:
    """Parse with the existing reader for a safe, fingerprinted summary.

    Returns ``{}`` for artifact types without a local preview parser; the server
    remains the authority for those.
    """
    parser = _PREVIEW.get(artifact_type)
    return parser(document) if parser else {}


def _ingest_one(
    client: Any,
    api_url: str,
    token: str,
    *,
    project_id: str,
    project_name: str,
    artifact_type: str,
    document: dict[str, Any],
    repository_ref: str,
    commit_sha: str,
) -> dict[str, Any]:
    endpoint = api_url.rstrip("/") + "/v1/dbt/artifacts"
    payload = {
        "project_id": project_id,
        "project_name": project_name,
        "artifact_type": artifact_type,
        "artifact": document,
        "repository_ref": repository_ref,
        "commit_sha": commit_sha,
    }
    response = client.post(
        endpoint,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code >= 400:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:512]
        raise CliError(f"ingestion of {artifact_type} failed with HTTP {response.status_code}: {detail}")
    return response.json()


def _resolve_token(token_env: str) -> str:
    token = os.environ.get(token_env, "")
    if not token:
        raise CliError(f"no bearer token in environment variable {token_env!r}")
    return token


def _build_client(timeout: float) -> Any:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise CliError("httpx is required for ingestion; install integrations/dbt/requirements.txt") from exc
    return httpx.Client(timeout=timeout)


def run_ingest(args: argparse.Namespace, client: Any | None = None) -> int:
    """Drive ingestion for the provided artifacts. ``client`` is injectable for tests."""
    artifacts: list[tuple[str, Path]] = []
    if args.manifest:
        artifacts.append(("manifest", args.manifest))
    if args.run_results:
        artifacts.append(("run_results", args.run_results))
    if args.catalog:
        artifacts.append(("catalog", args.catalog))
    if args.freshness:
        artifacts.append(("freshness", args.freshness))
    if not artifacts:
        raise CliError("provide at least one of --manifest / --run-results / --catalog / --freshness")

    # Ingest in dependency order regardless of flag order.
    artifacts.sort(key=lambda item: _ARTIFACT_ORDER.index(item[0]))

    documents: list[tuple[str, dict[str, Any]]] = []
    for artifact_type, path in artifacts:
        document = _load_json(path)
        summary = preview(artifact_type, document)
        if summary:
            node_count = len(summary.get("nodes", summary.get("results", [])))
            print(f"loaded {artifact_type} from {path}: {node_count} node(s) [preview-only, no SQL emitted]")
        else:
            print(f"loaded {artifact_type} from {path} [server-side parse]")
        documents.append((artifact_type, document))

    if args.dry_run:
        print("dry-run: parsed locally, nothing sent")
        return 0

    token = _resolve_token(args.token_env)
    owns_client = client is None
    client = client or _build_client(args.timeout)
    try:
        for artifact_type, document in documents:
            result = _ingest_one(
                client,
                args.api_url,
                token,
                project_id=args.project_id,
                project_name=args.project_name,
                artifact_type=artifact_type,
                document=document,
                repository_ref=args.repository_ref,
                commit_sha=args.commit_sha,
            )
            print(
                f"ingested {artifact_type}: event_id={result.get('event_id')} "
                f"status={result.get('status')} fingerprint={result.get('artifact_fingerprint')}"
            )
    finally:
        if owns_client and hasattr(client, "close"):
            client.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dataobs dbt", description="DataObs dbt artifact ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="load dbt artifacts and drive POST /api/v1/dbt/artifacts")
    ingest.add_argument("--api-url", required=True, help="DataObs API base, e.g. https://host/api")
    ingest.add_argument("--token-env", default="DATAOBS_TOKEN", help="env var holding the bearer token")
    ingest.add_argument("--project-id", required=True)
    ingest.add_argument("--project-name", required=True)
    ingest.add_argument("--manifest", type=Path, help="path to target/manifest.json")
    ingest.add_argument("--run-results", type=Path, help="path to target/run_results.json")
    ingest.add_argument("--catalog", type=Path, help="path to target/catalog.json")
    ingest.add_argument("--freshness", type=Path, help="path to sources.json / freshness artifact")
    ingest.add_argument("--repository-ref", default="unknown", help="git ref of the dbt project")
    ingest.add_argument("--commit-sha", default="unknown", help="git commit SHA of the dbt project")
    ingest.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    ingest.add_argument("--dry-run", action="store_true", help="parse locally, do not send")
    ingest.set_defaults(func=run_ingest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
