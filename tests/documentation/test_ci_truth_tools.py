from __future__ import annotations

import copy
import json
import subprocess

import pytest

from scripts.capability_diff import diff, load
from scripts.resolve_ci_base import ZERO_SHA, resolve
from scripts.validate_capability_ledger import load as load_ledger
from scripts.validate_capability_ledger import validate

HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def test_resolve_pull_request_base():
    assert resolve({"pull_request": {"base": {"sha": HEAD}}}, "pull_request", None, "HEAD") == HEAD


def test_resolve_push_base():
    assert resolve({"before": HEAD}, "push", None, "HEAD") == HEAD


def test_resolve_workflow_dispatch_explicit_input():
    assert resolve({"inputs": {"base_ref": HEAD}}, "workflow_dispatch", None, "HEAD") == HEAD


def test_resolve_all_zero_push_uses_merge_base():
    assert resolve({"before": ZERO_SHA}, "push", None, "HEAD") == HEAD


def test_invalid_base_reference_is_named():
    with pytest.raises(ValueError):
        resolve({"before": "not-a-ref"}, "push", None, "HEAD")


def test_missing_historical_ledger_is_bootstrap(tmp_path):
    # A valid commit with a non-existent path is intentionally an empty old ledger.
    assert load(HEAD, "missing-ledger.yaml", missing_ok=True) == {"capabilities": []}


def test_special_state_transitions_are_never_dropped():
    base = {"capabilities": [{"id": "x.y", "state": "foundation"}]}
    deprecated = copy.deepcopy(base)
    deprecated["capabilities"][0]["state"] = "deprecated"
    report = diff(base, deprecated)
    assert report["moved_to_deprecated"] == ["x.y"]
    assert diff(deprecated, base)["restored_from_deprecated"] == ["x.y"]
    optional = copy.deepcopy(base)
    optional["capabilities"][0]["state"] = "optional_integration"
    assert diff(base, optional)["moved_to_optional_integration"] == ["x.y"]
    assert diff(optional, base)["restored_from_optional_integration"] == ["x.y"]


@pytest.mark.parametrize("capability_id", ["ai_agent.advisor", "finops_cost.optimization"])
def test_future_capability_cannot_claim_empty_validated_state(capability_id):
    ledger = load_ledger()
    candidate = copy.deepcopy(ledger["capabilities"][0])
    candidate.update(id=capability_id, state="validated")
    candidate["implementation"] = {
        key: [] for key in ("code_paths", "api_paths", "ui_routes", "storage_resources", "migrations")
    }
    candidate["validation"] = {key: "not_applicable" for key in candidate["validation"]}
    ledger["capabilities"] = [candidate]
    errors = validate(ledger)
    assert any("meaningful implementation surface" in error for error in errors)
    assert any("applicable passed evidence" in error for error in errors)
