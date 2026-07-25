"""Canonical commit provenance shared by every Data Product evidence writer."""

from __future__ import annotations

import os
import re
import subprocess

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def expected_certification_sha(explicit: str | None = None) -> str | None:
    """Return the independently supplied expected SHA.

    Producer identity cannot satisfy independent expectation: neither
    ``DATA_PRODUCT_CERTIFICATION_SHA`` nor ``GITHUB_SHA`` is consulted here.
    An explicit CLI value wins over ``EXPECTED_HOSTED_SHA`` and every selected
    value is validated before use.
    """
    value = explicit
    if value is None:
        value = os.getenv("EXPECTED_HOSTED_SHA")
    if value is not None and not SHA_RE.fullmatch(value):
        raise ValueError("expected certification SHA must be a lowercase 40-character hexadecimal SHA")
    return value


def certification_commit_sha() -> str:
    """Return the explicit certification SHA, falling back to local Git only.

    GitHub jobs must set ``DATA_PRODUCT_CERTIFICATION_SHA``.  In particular we
    intentionally do not consult ``GITHUB_SHA``: for pull requests it denotes
    GitHub's synthetic merge commit, not the checked-out certification head.
    """
    value = os.getenv("DATA_PRODUCT_CERTIFICATION_SHA")
    if value is None:
        value = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if not SHA_RE.fullmatch(value):
        raise ValueError("DATA_PRODUCT_CERTIFICATION_SHA must be a lowercase 40-character hexadecimal SHA")
    return value
