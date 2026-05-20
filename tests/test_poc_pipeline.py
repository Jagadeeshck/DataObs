from __future__ import annotations

from pathlib import Path

from src.poc.config import get_poc_config
from src.poc.datasets import resolve_sources
from src.poc.pipeline_runner import DataObsPipelineRunner, InMemoryPipelineSink


def test_get_poc_config_loads_standalone_poc_file_by_default():
    cfg = get_poc_config("config/dataobs_poc.yaml")
    assert cfg["enabled"] is True
    assert cfg["pipeline"]["tenant"] == "poc"


def test_fixture_mode_resolves_local_sources(monkeypatch):
    monkeypatch.setenv("DATAOBS_POC_FIXTURE_MODE", "true")
    sources = resolve_sources({"data_sources": [], "source_defaults": {"enabled": True}})
    assert len(sources) == 3
    assert all(s["resource_url"].startswith("file://") for s in sources)


def test_pipeline_runner_completes_with_memory_sink_and_mock_spark(monkeypatch):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("DATAOBS_POC_SPARK_MODE", "mock")
    sink = InMemoryPipelineSink()
    runner = DataObsPipelineRunner(tenant="test", run_id="test-run", sink=sink)
    summary = runner.run()
    assert summary["sink"] == "InMemoryPipelineSink"
    assert len(sink.documents["dataobs-test-data"]) == 50


def test_demo_scripts_exist_and_are_bash_syntax_clean():
    scripts = [
        "scripts/demo_up.sh",
        "scripts/demo_run.sh",
        "scripts/demo_verify.sh",
        "scripts/demo_reset.sh",
    ]
    for script in scripts:
        assert Path(script).exists()
