from pathlib import Path

import pytest

from src.poc.pipeline_runner import DataObsPipelineRunner
from src.poc.scenarios.road_safety.generator import generate_scaled
from src.poc.scenarios.road_safety.pipeline import run_road_safety_scenario
from src.poc.spark_metrics import metric_doc


def test_generator_small(tmp_path: Path):
    out = generate_scaled(Path("fixtures/poc/road_safety"), tmp_path, scale="small")
    assert out["accidents"].exists()
    assert out["vehicles"].exists()


def test_good_run_quality_summary(tmp_path: Path):
    generate_scaled(Path("fixtures/poc/road_safety"), tmp_path, scale="small")
    res = run_road_safety_scenario(tmp_path, "RUN1", run_mode="good")
    assert "dataobs-rs-accident-facts" in res["outputs"]
    assert all(q["status"] in {"pass", "warn", "fail"} for q in res["quality"])


def test_road_safety_outputs_include_required_indices(tmp_path: Path):
    generate_scaled(Path("fixtures/poc/road_safety"), tmp_path, scale="small")
    res = run_road_safety_scenario(tmp_path, "RUNX", run_mode="good")
    required = {
        "dataobs-rs-accident-facts",
        "dataobs-rs-authority-risk-summary",
        "dataobs-rs-road-risk-summary",
        "dataobs-rs-vehicle-risk-summary",
        "dataobs-rs-casualty-severity-summary",
    }
    assert required.issubset(set(res["outputs"].keys()))


def test_road_safety_spark_metrics_non_empty(tmp_path: Path):
    generate_scaled(Path("fixtures/poc/road_safety"), tmp_path, scale="small")
    res = run_road_safety_scenario(tmp_path, "RUNY", run_mode="good")
    assert len(res["spark_metrics"]) > 0


def test_bad_run_injection(tmp_path: Path):
    generate_scaled(Path("fixtures/poc/road_safety"), tmp_path, scale="small")
    res = run_road_safety_scenario(tmp_path, "RUN2", run_mode="bad")
    assert any(q["status"] == "fail" for q in res["quality"])


def test_spark_metric_shape():
    doc = metric_doc("R", "stage", 100, 90)
    for k in ["run_id", "stage_name", "stage_duration_seconds", "input_rows", "output_rows", "status", "error_count"]:
        assert k in doc


def test_runner_road_safety_fails_when_outputs_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DATAOBS_DEMO_SCENARIO", "road_safety")
    monkeypatch.setenv("DATAOBS_DEMO_RUN_MODE", "good")
    monkeypatch.setenv("DATAOBS_DEMO_SCALE", "small")

    import src.poc.scenarios.road_safety.generator as generator_mod
    import src.poc.scenarios.road_safety.pipeline as pipeline_mod

    monkeypatch.setattr(generator_mod, "generate_scaled", lambda *a, **k: {"accidents": tmp_path / "accidents.csv"})

    def _bad_scenario(*_args, **_kwargs):
        return {"outputs": {"dataobs-rs-accident-facts": [{"a": 1}]}, "quality": [], "spark_metrics": [{"m": 1}]}

    monkeypatch.setattr(pipeline_mod, "run_road_safety_scenario", _bad_scenario)
    runner = DataObsPipelineRunner()
    with pytest.raises(RuntimeError, match="missing required output indices"):
        runner.run()


def test_poc_elastic_stack_version_pins_are_consistent():
    repo = Path(__file__).resolve().parents[1]
    env_text = (repo / ".env.poc").read_text()
    compose_text = (repo / "docker-compose.poc.yml").read_text()
    root_compose_text = (repo / "docker-compose.yml").read_text()
    example_env_text = (repo / ".env.example").read_text()

    assert "ELK_VERSION=9.4.2" in env_text
    assert "ELK_VERSION=9.4.2" in example_env_text
    assert "docker.elastic.co/elasticsearch/elasticsearch:${ELK_VERSION:-9.4.2}" in compose_text
    assert "docker.elastic.co/kibana/kibana:${ELK_VERSION:-9.4.2}" in compose_text
    assert "docker.elastic.co/elastic-agent/elastic-agent:${ELK_VERSION:-9.4.2}" in compose_text
    assert "ELK_VERSION: ${ELK_VERSION:-9.4.2}" in compose_text
    assert "docker.elastic.co/elasticsearch/elasticsearch:${ELK_VERSION:-9.4.2}" in root_compose_text
    assert "docker.elastic.co/kibana/kibana:${ELK_VERSION:-9.4.2}" in root_compose_text


def test_poc_elastic_stack_has_no_stale_active_version_references():
    repo = Path(__file__).resolve().parents[1]
    allowed_history = {
        "docs/poc-setup.md",
    }
    stale_tokens = ("9." + "4.0", "9." + "3.0", "9." + "3.3")
    offenders = []

    for path in repo.rglob("*"):
        if path.is_dir() or ".git" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(repo).as_posix()
        if rel in allowed_history:
            continue
        if any(token in text for token in stale_tokens):
            offenders.append(rel)

    assert offenders == []


def test_fleet_package_policies_resolve_semver_versions_not_latest_literals():
    repo = Path(__file__).resolve().parents[1]
    compose_text = (repo / "docker-compose.poc.yml").read_text()

    assert "APM_VER=$$(" in compose_text
    assert "DOCKER_VER=$$(" in compose_text
    assert r"\"version\":\"$${APM_VER}\"" in compose_text
    assert r"\"version\":\"$${DOCKER_VER}\"" in compose_text
    assert r"\"version\":\"latest\"" not in compose_text
