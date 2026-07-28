"""Verify that required hosted workflows certified one exact commit.

The verifier deliberately treats reruns as ambiguous.  A release operator must
resolve multiple successful candidates rather than allowing list ordering to
silently select evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any

DEFAULT_WORKFLOWS = (
    ("CI", "ci.yml"),
    ("Data Product runtime certification", "data-product-runtime.yml"),
    ("Data Product reconciliation certification", "data-product-membership.yml"),
)
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


class CertificationError(RuntimeError):
    """The requested commit does not have unambiguous successful evidence."""


def github_get(url: str, token: str) -> Mapping[str, Any]:
    """Issue an authenticated GET without ever logging the credential."""
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.load(response)


def verify_certification(
    repository: str,
    expected_sha: str,
    *,
    token: str,
    workflows: Sequence[tuple[str, str]] = DEFAULT_WORKFLOWS,
    get: Callable[[str, str], Mapping[str, Any]] = github_get,
) -> list[dict[str, Any]]:
    """Return the single accepted run for every required workflow."""
    if not _REPOSITORY.fullmatch(repository):
        raise ValueError("repository must use owner/name syntax")
    if not _SHA.fullmatch(expected_sha):
        raise ValueError("expected SHA must be a full 40-character commit SHA")
    accepted = []
    for label, workflow in workflows:
        query = urllib.parse.urlencode({"head_sha": expected_sha, "status": "completed", "per_page": 100})
        url = (
            f"https://api.github.com/repos/{repository}/actions/workflows/"
            f"{urllib.parse.quote(workflow, safe='')}/runs?{query}"
        )
        payload = get(url, token)
        runs = payload.get("workflow_runs")
        if not isinstance(runs, list) or not runs:
            raise CertificationError(f"no completed {label} runs for {expected_sha}")
        candidates = [
            run
            for run in runs
            if run.get("head_sha") == expected_sha
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
        ]
        if len(candidates) != 1:
            raise CertificationError(
                f"expected one successful {label} run for {expected_sha}; " f"found {len(candidates)}"
            )
        run = candidates[0]
        if not isinstance(run.get("id"), int) or not run.get("html_url"):
            raise CertificationError(f"{label} run metadata is incomplete")
        accepted.append({"workflow": label, "id": run["id"], "url": run["html_url"]})
    return accepted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN")
    if not token:
        parser.error("GH_TOKEN is required")
    result = verify_certification(args.repository, args.expected_sha, token=token)
    encoded = json.dumps(result, separators=(",", ":"))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output:
            output.write(encoded + "\n")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
