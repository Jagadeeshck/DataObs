from __future__ import annotations

from pathlib import Path

from src.poc.config import get_poc_config
from src.poc.pipeline_runner import DataObsPipelineRunner, InMemoryPipelineSink


def test_get_poc_config_loads_standalone_poc_file_by_default():
    cfg = get_poc_config("config/dataobs_poc.yaml")

    assert cfg["enabled"] is True
    assert cfg["pipeline"]["tenant"] == "poc"
    assert cfg["elasticsearch"]["host"].startswith("http")
    assert cfg["runtime"]["raw_download_dir"]


def test_get_poc_config_expands_environment_defaults(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "dataobs_poc.yaml"
    config_path.write_text(
        """
        tenant: ${TENANT_NAME:-poc}
        elasticsearch:
          host: ${ES_URL:-http://localhost:9200}
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("ES_URL", "http://elasticsearch:9200")

    cfg = get_poc_config(str(config_path))

    assert cfg["tenant"] == "poc"
    assert cfg["elasticsearch"]["host"] == "http://elasticsearch:9200"
    assert cfg["enabled"] is True


def test_pipeline_runner_completes_with_memory_sink_and_mock_spark(monkeypatch):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("DATAOBS_POC_SPARK_MODE", "mock")
    sink = InMemoryPipelineSink()
    runner = DataObsPipelineRunner(tenant="test", run_id="test-run", sink=sink)

    summary = runner.run()

    assert summary["ingested_rows"] == 50
    assert summary["transformed_rows"] == 93
    assert summary["sink"] == "InMemoryPipelineSink"
    assert len(sink.documents["dataobs-test-data"]) == 50
    assert len(sink.documents["dataobs-spark-results"]) == 93
    assert len(sink.documents["dataobs-lineage"]) == 1
