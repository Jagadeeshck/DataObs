#!/usr/bin/env python3
"""Static policy checks for the hosted certification workflow."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from scripts.certification.validate_job_results import ALL_JOBS, REQUIRED_JOBS
except ModuleNotFoundError:  # direct script execution
    from validate_job_results import ALL_JOBS, REQUIRED_JOBS

WORKFLOW = Path(".github/workflows/ci.yml")
JOB_IDS = {
    "migrations-incidents": "certification-migrations-incidents",
    "postgres": "certification-postgres",
    "kafka": "certification-kafka",
    "openlineage-product": "certification-openlineage-product",
    "browser": "certification-browser",
    "security": "certification-security",
}
WRITE_BACKED = set(JOB_IDS)


def _job(text: str, job_id: str) -> str:
    match = re.search(rf"^  {re.escape(job_id)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)", text, re.M | re.S)
    return match.group("body") if match else ""


def validate(text: str) -> list[str]:
    errors: list[str] = []
    option_match = re.search(r"options:\s*\[([^]]+)\]", text)
    options = {v.strip() for v in option_match.group(1).split(",")} if option_match else set()
    if options != set(REQUIRED_JOBS):
        errors.append(f"dispatch options {sorted(options)} do not match supported scopes")
    for scope, required in REQUIRED_JOBS.items():
        if not (required - {"contracts"}):
            errors.append(f"{scope} selects no functional job")
        for short in required - {"contracts"}:
            body = _job(text, JOB_IDS[short])
            if scope != "all" and f"inputs.certification_scope == '{scope}'" not in body:
                errors.append(f"{scope} does not select {JOB_IDS[short]}")
    if REQUIRED_JOBS["all"] != ALL_JOBS:
        errors.append("all does not require every mandatory job")
    for short, job_id in JOB_IDS.items():
        body = _job(text, job_id)
        condition = next((line for line in body.splitlines() if line.strip().startswith("if:")), "")
        operands = re.findall(r"inputs\.certification_scope == '([^']+)'", condition)
        if len(operands) != len(set(operands)):
            errors.append(f"{job_id} condition contains duplicate operands")
        migration = body.find("./scripts/certification/apply_migrations.sh")
        assertion = body.find("Run live assertions")
        browser_assertion = body.find("Run browser live assertions")
        first_test = assertion if assertion >= 0 else browser_assertion
        if short in WRITE_BACKED and (migration < 0 or first_test < 0 or migration > first_test):
            errors.append(f"{job_id} must migrate before live assertions")
        if "if: always()" not in body:
            errors.append(f"{job_id} teardown must use if: always()")
    kafka = _job(text, JOB_IDS["kafka"])
    if not (0 <= kafka.find("create_topics.sh") < kafka.find("Run live assertions")):
        errors.append("Kafka setup must precede Kafka tests")
    browser = _job(text, JOB_IDS["browser"])
    if "Start production Console stack" not in browser:
        errors.append("browser job does not start production Console")
    security = _job(text, JOB_IDS["security"])
    if "CERTIFICATION_PROFILE=cert-security" not in security:
        errors.append("security job does not start runtime dependencies")
    return errors


def main() -> int:
    errors = validate(WORKFLOW.read_text())
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"{WORKFLOW}: certification scope semantics valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
