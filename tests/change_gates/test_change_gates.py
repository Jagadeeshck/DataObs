from services.change_gates.changed_models import detect_changes, parse_manifest
from services.change_gates.drift_check import compare_profiles
from services.change_gates.evaluator import evaluate
from services.change_gates.models import ChangeGatePolicy, GateMode
from services.change_gates.repository import MemoryChangeGateRepository


def manifest(nodes):
    return {"metadata": {}, "nodes": nodes}


def model(name, checksum="x", columns=None):
    return {
        "resource_type": "model",
        "name": name,
        "checksum": {"checksum": checksum},
        "columns": columns or {},
        "depends_on": {"nodes": []},
    }


def test_changes_and_rename_are_deterministic():
    base = manifest({"model.p.old": model("old", "same"), "model.p.modified": model("modified", "a")})
    head = manifest(
        {
            "model.p.new": model("new", "same"),
            "model.p.modified": model("modified", "b"),
            "model.p.added": model("added"),
        }
    )
    changes = detect_changes(base, head)
    assert [(x["unique_id"], x["change_type"]) for x in changes] == [
        ("model.p.added", "added"),
        ("model.p.modified", "modified"),
        ("model.p.old", "renamed_candidate"),
    ]


def test_raw_sql_rejected():
    try:
        parse_manifest(manifest({"model.p.x": {**model("x"), "raw_sql": "select secret"}}))
    except ValueError as exc:
        assert "unsafe dbt field" in str(exc)
    else:
        raise AssertionError("unsafe artifact accepted")


def test_drift_thresholds():
    p = ChangeGatePolicy()
    values = compare_profiles(
        {"row_count": 1000, "null_rate": 0.005, "cardinality": 100},
        {"row_count": 650, "null_rate": 0.12, "cardinality": 100},
        p.drift_thresholds,
    )
    assert {x["metric"]: x["status"] for x in values} == {
        "row_count": "failed",
        "null_rate": "warning",
        "cardinality": "passed",
    }


def test_required_missing_evidence_is_partial_and_replay_idempotent():
    kwargs = dict(
        tenant_id="t",
        environment="ci",
        repository="org/repo",
        project_id="p",
        pr_id="1",
        base_sha="a" * 40,
        head_sha="b" * 40,
        base_manifest=manifest({}),
        head_manifest=manifest({}),
        policy=ChangeGatePolicy(required_evidence=("lineage",)),
    )
    first, second = evaluate(**kwargs), evaluate(**kwargs)
    assert first["status"] == "partial" and first["evaluation_id"] == second["evaluation_id"]
    changed = evaluate(**{**kwargs, "head_sha": "c" * 40})
    assert changed["evaluation_id"] != first["evaluation_id"]


def test_advisory_downgrades_blocking_exit_status():
    result = evaluate(
        tenant_id="t",
        environment="ci",
        repository="r",
        project_id="p",
        pr_id="1",
        base_sha="a" * 40,
        head_sha="b" * 40,
        base_manifest=manifest({"model.p.x": model("x")}),
        head_manifest=manifest({}),
        policy=ChangeGatePolicy(gate_mode=GateMode.ADVISORY),
        run_results={"results": []},
    )
    assert result["status"] == "warning" and "model_removed" in result["blocking_reasons"]


def test_memory_repository_tenant_isolation():
    repo = MemoryChangeGateRepository()
    item = {"evaluation_id": "one", "status": "running"}
    repo.start_evaluation("a", "ci", item)
    assert repo.get_evaluation("a", "ci", "one") and repo.get_evaluation("b", "ci", "one") is None
