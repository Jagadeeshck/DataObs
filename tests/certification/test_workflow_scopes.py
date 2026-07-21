import json
from pathlib import Path

import pytest

from scripts.certification.validate_job_results import ALL_JOBS, REQUIRED_JOBS, validate
from scripts.certification.validate_workflow_scopes import validate as validate_workflow


@pytest.mark.parametrize("scope", sorted(REQUIRED_JOBS))
def test_focused_scope_accepts_only_expected_skips(scope):
    required = REQUIRED_JOBS[scope]
    results = {job: ("success" if job in required else "skipped") for job in ALL_JOBS}
    summary = validate(scope, results)
    assert summary["errors"] == []
    assert summary["partial"] is (scope != "all")


def test_required_skip_is_rejected():
    results = {job: "skipped" for job in ALL_JOBS}
    results["contracts"] = "success"
    assert validate("kafka", results)["errors"]


def test_failure_in_unselected_job_is_rejected():
    results = {job: "skipped" for job in ALL_JOBS}
    results.update(contracts="success", kafka="success", postgres="failure")
    assert validate("kafka", results)["errors"]


def test_all_requires_every_job():
    results = {job: "success" for job in ALL_JOBS}
    results["security"] = "skipped"
    assert validate("all", results)["errors"]


def test_product_selects_product_job():
    assert REQUIRED_JOBS["product"] == {"contracts", "openlineage-product"}


def test_checked_in_workflow_has_valid_semantics():
    assert validate_workflow(Path(".github/workflows/ci.yml").read_text()) == []
