#!/usr/bin/env python3
"""Reject empty, malformed, skipped, or failing mandatory test runs."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def validate(path: Path) -> None:
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    if root.tag not in {"testsuites", "testsuite"} or not cases:
        raise ValueError("mandatory JUnit contains no tests")
    if any(case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")):
        raise ValueError("mandatory JUnit contains failed or skipped tests")
    suites = list(root.iter("testsuite"))
    if sum(int(s.get("tests", "0")) for s in suites) != len(cases):
        raise ValueError("mandatory JUnit test counts disagree")
    if any(int(s.get(key, "0")) for s in suites for key in ("failures", "errors", "skipped")):
        raise ValueError("mandatory JUnit suite is not passing")


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        validate(Path(argument))
    if len(sys.argv) == 1:
        raise SystemExit("at least one JUnit path is required")
