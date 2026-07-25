"""
Tests for DataObs dbt integration.

Covers:
  1. run_results.json schema validation (happy path + all error cases)
  2. OTel span attribute compliance with stable DB semconv spec
  3. db.system.name adapter mapping
  4. db.operation.name resolution per resource_type
  5. db.collection.name / db.namespace extraction
  6. error.type set on failure statuses
  7. dbt Cloud poller semconv attributes
  8. Edge cases: empty results, missing fields, unknown schema version

Strategy for span capture:
  Patch the module-level ``_tracer`` in parse_run_results directly with a
  tracer backed by InMemorySpanExporter. This avoids the OTel SDK restriction
  that prevents overriding the global TracerProvider after first initialisation.

Run with:
    pytest tests/test_dbt_integration.py -v

Resolves: https://github.com/Jagadeeshck/DataObs/issues/29
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

# ── sys.path fixup ────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
for _candidate in (_ROOT,):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import integrations.dbt.dbt_cloud_poller as _poller_module
import integrations.dbt.parse_run_results as _prr_module
from integrations.dbt.dbt_cloud_poller import DbtCloudPoller
from integrations.dbt.parse_run_results import (
    _REQUIRED_METADATA_FIELDS,
    _REQUIRED_RESULT_FIELDS,
    _REQUIRED_TOP_LEVEL,
    _SUPPORTED_SCHEMA_VERSIONS,
    _resolve_collection_name,
    _resolve_db_system,
    _resolve_operation_name,
    _validate_schema,
    parse_and_emit,
)

# ── Span capture fixture ──────────────────────────────────────────────────────


@pytest.fixture()
def exporter() -> Generator[InMemorySpanExporter, None, None]:
    """
    Patch the module-level _tracer in both dbt modules with one backed
    by an InMemorySpanExporter.  Avoids the OTel SDK restriction that
    prevents overriding the global TracerProvider after first init.
    """
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))

    prr_tracer = provider.get_tracer("dataobs.dbt", "0.2.0")
    poller_tracer = provider.get_tracer("dataobs.dbt.cloud", "0.2.0")

    with (
        patch.object(_prr_module, "_tracer", prr_tracer),
        patch.object(_poller_module, "_tracer", poller_tracer),
    ):
        yield exp
        exp.clear()


# ── Fixture helpers ───────────────────────────────────────────────────────────


def _make_run_results(
    *,
    adapter_type: str = "postgres",
    schema_version: str = "https://schemas.getdbt.com/dbt/run-results/v5/run-results.json",
    results: list[dict[str, Any]] | None = None,
    elapsed_time: float = 5.23,
) -> dict[str, Any]:
    if results is None:
        results = [_make_result()]
    return {
        "metadata": {
            "dbt_schema_version": schema_version,
            "dbt_version": "1.7.0",
            "generated_at": "2024-03-01T10:00:00.000000Z",
            "invocation_id": "test-invocation-abc123",
            "env": {},
            "adapter_type": adapter_type,
        },
        "elapsed_time": elapsed_time,
        "results": results,
        "args": {},
    }


def _make_result(
    *,
    resource_type: str = "model",
    name: str = "orders",
    schema: str = "analytics",
    database: str = "mydb",
    relation_name: str = '"mydb"."analytics"."orders"',
    status: str = "success",
    rows_affected: int = 1200,
    execution_time: float = 2.5,
    materialized: str = "table",
) -> dict[str, Any]:
    return {
        "status": status,
        "unique_id": f"model.mypackage.{name}",
        "timing": [
            {"name": "compile", "started_at": "2024-03-01T10:00:00Z", "completed_at": "2024-03-01T10:00:01Z"},
            {"name": "execute", "started_at": "2024-03-01T10:00:01Z", "completed_at": "2024-03-01T10:00:03Z"},
        ],
        "execution_time": execution_time,
        "message": None,
        "failures": None,
        "node": {
            "unique_id": f"model.mypackage.{name}",
            "resource_type": resource_type,
            "name": name,
            "schema": schema,
            "database": database,
            "relation_name": relation_name,
            "package_name": "mypackage",
            "original_file_path": f"models/{name}.sql",
            "config": {"materialized": materialized},
        },
        "adapter_response": {
            "_message": "SUCCESS 1200",
            "code": "SUCCESS",
            "rows_affected": rows_affected,
        },
    }


def _emit_to_tmp(data: dict[str, Any], suffix: str = "") -> list[ReadableSpan]:
    """Write *data* to a temp file, call parse_and_emit, return nothing (use exporter)."""
    tmp = Path(f"/tmp/test_run_results{suffix}.json")
    tmp.write_text(json.dumps(data))
    parse_and_emit(tmp)


# ── Schema validation tests ───────────────────────────────────────────────────


class TestSchemaValidation:
    def test_valid_document_passes(self) -> None:
        _validate_schema(_make_run_results())

    def test_missing_top_level_metadata_raises(self) -> None:
        data = _make_run_results()
        del data["metadata"]
        with pytest.raises(ValueError, match="missing required top-level fields"):
            _validate_schema(data)

    def test_missing_top_level_results_raises(self) -> None:
        data = _make_run_results()
        del data["results"]
        with pytest.raises(ValueError, match="missing required top-level fields"):
            _validate_schema(data)

    def test_metadata_not_dict_raises(self) -> None:
        data = _make_run_results()
        data["metadata"] = "not-a-dict"
        with pytest.raises(ValueError, match="metadata.*must be a dict"):
            _validate_schema(data)

    @pytest.mark.parametrize("missing_field", sorted(_REQUIRED_METADATA_FIELDS))
    def test_missing_metadata_field_raises(self, missing_field: str) -> None:
        data = _make_run_results()
        del data["metadata"][missing_field]
        with pytest.raises(ValueError, match=f"metadata missing fields.*{missing_field}"):
            _validate_schema(data)

    def test_results_not_list_raises(self) -> None:
        data = _make_run_results()
        data["results"] = {"oops": "not a list"}
        with pytest.raises(ValueError, match="results.*must be a list"):
            _validate_schema(data)

    def test_result_not_dict_raises(self) -> None:
        data = _make_run_results(results=["not-a-dict"])
        with pytest.raises(ValueError, match=r"results\[0\] must be a dict"):
            _validate_schema(data)

    @pytest.mark.parametrize("missing_field", sorted(_REQUIRED_RESULT_FIELDS))
    def test_missing_result_field_raises(self, missing_field: str) -> None:
        result = _make_result()
        del result[missing_field]
        data = _make_run_results(results=[result])
        with pytest.raises(ValueError, match=f"results\\[0\\] missing required fields.*{missing_field}"):
            _validate_schema(data)

    def test_timing_not_list_raises(self) -> None:
        result = _make_result()
        result["timing"] = "not-a-list"
        data = _make_run_results(results=[result])
        with pytest.raises(ValueError, match=r"results\[0\].timing must be a list"):
            _validate_schema(data)

    def test_empty_results_list_is_valid(self) -> None:
        _validate_schema(_make_run_results(results=[]))

    def test_unknown_schema_version_warns(self) -> None:
        data = _make_run_results(schema_version="https://schemas.getdbt.com/dbt/run-results/v99/run-results.json")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _validate_schema(data)
        assert any("Unrecognised dbt run_results schema version" in str(w.message) for w in caught)

    def test_all_supported_schema_versions_pass(self) -> None:
        for version in _SUPPORTED_SCHEMA_VERSIONS:
            _validate_schema(_make_run_results(schema_version=version))


# ── db.system.name mapping tests ──────────────────────────────────────────────


class TestDbSystemNameMapping:
    @pytest.mark.parametrize(
        "adapter,expected",
        [
            ("postgres", "postgresql"),
            ("postgresql", "postgresql"),
            ("redshift", "aws.redshift"),
            ("snowflake", "other_sql"),
            ("bigquery", "other_sql"),
            ("trino", "trino"),
            ("mysql", "mysql"),
            ("sqlserver", "microsoft.sql_server"),
            ("clickhouse", "clickhouse"),
            ("databricks", "other_sql"),
            ("duckdb", "other_sql"),
            ("spark", "other_sql"),
            ("unknown_adapter", "other_sql"),
            ("", "other_sql"),
            ("POSTGRES", "postgresql"),
        ],
    )
    def test_adapter_mapping(self, adapter: str, expected: str) -> None:
        assert _resolve_db_system(adapter) == expected

    def test_all_mapped_values_are_nonempty_strings(self) -> None:
        from integrations.dbt.parse_run_results import _ADAPTER_TO_DB_SYSTEM

        for adapter, db_system in _ADAPTER_TO_DB_SYSTEM.items():
            assert isinstance(db_system, str) and db_system


# ── db.operation.name resolution tests ───────────────────────────────────────


class TestDbOperationNameResolution:
    @pytest.mark.parametrize(
        "resource_type,expected_prefix",
        [
            ("model", "run_model"),
            ("test", "test"),
            ("seed", "seed"),
            ("snapshot", "snapshot"),
            ("analysis", "run_analysis"),
            ("", "run"),
        ],
    )
    def test_operation_name_by_resource_type(self, resource_type: str, expected_prefix: str) -> None:
        result = _resolve_operation_name(resource_type, {})
        assert result.startswith(expected_prefix)

    def test_generic_test_uses_test_metadata_name(self) -> None:
        node = {"test_metadata": {"name": "not_null"}}
        assert _resolve_operation_name("test", node) == "test.not_null"

    def test_generic_test_without_metadata(self) -> None:
        assert _resolve_operation_name("test", {}) == "test"


# ── db.collection.name resolution tests ──────────────────────────────────────


class TestDbCollectionNameResolution:
    def test_relation_name_preferred_over_node_name(self) -> None:
        node = {"relation_name": '"mydb"."analytics"."orders"', "name": "orders"}
        result = _resolve_collection_name(node)
        assert result  # non-empty
        assert "orders" in result

    def test_fallback_to_node_name(self) -> None:
        node = {"name": "stg_customers"}
        assert _resolve_collection_name(node) == "stg_customers"

    def test_empty_node_returns_empty(self) -> None:
        assert _resolve_collection_name({}) == ""

    def test_backtick_quotes_stripped(self) -> None:
        node = {"relation_name": "`myproject.myds.orders`"}
        result = _resolve_collection_name(node)
        assert not result.startswith("`") and not result.endswith("`")


# ── OTel span attribute compliance tests ─────────────────────────────────────


class TestSpanSemconvCompliance:
    def _spans(
        self,
        exporter: InMemorySpanExporter,
        adapter_type: str = "postgres",
        results: list[dict[str, Any]] | None = None,
        suffix: str = "",
    ) -> list[ReadableSpan]:
        data = _make_run_results(adapter_type=adapter_type, results=results)
        _emit_to_tmp(data, suffix)
        return exporter.get_finished_spans()

    def _root(self, spans: list[ReadableSpan]) -> ReadableSpan:
        matches = [s for s in spans if s.name.startswith("dbt run")]
        assert matches, f"No root span found in: {[s.name for s in spans]}"
        return matches[0]

    def _nodes(self, spans: list[ReadableSpan]) -> list[ReadableSpan]:
        return [s for s in spans if not s.name.startswith("dbt run")]

    def test_root_span_has_db_system_name(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, adapter_type="postgres", suffix="_sys")
        assert self._root(spans).attributes.get("db.system.name") == "postgresql"

    def test_root_span_has_db_operation_name(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_op")
        assert self._root(spans).attributes.get("db.operation.name") == "run"

    def test_root_span_kind_is_client(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_kind")
        assert self._root(spans).kind == SpanKind.CLIENT

    def test_node_span_has_db_system_name(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, adapter_type="redshift", suffix="_nodesys")
        for span in self._nodes(spans):
            assert span.attributes.get("db.system.name") == "aws.redshift"

    def test_node_span_has_db_operation_name(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_nodeop")
        for span in self._nodes(spans):
            op = span.attributes.get("db.operation.name")
            assert op and isinstance(op, str)

    def test_node_span_has_db_collection_name(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_nodecoll")
        for span in self._nodes(spans):
            assert "db.collection.name" in span.attributes

    def test_node_span_has_db_namespace(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_nodens")
        for span in self._nodes(spans):
            assert "db.namespace" in span.attributes

    def test_node_span_db_namespace_value(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, results=[_make_result(schema="raw_data")], suffix="_nsval")
        nodes = self._nodes(spans)
        assert nodes
        assert nodes[0].attributes.get("db.namespace") == "raw_data"

    def test_node_span_kind_is_client(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_nodekind")
        for span in self._nodes(spans):
            assert span.kind == SpanKind.CLIENT

    def test_node_span_name_pattern(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, results=[_make_result(name="orders")], suffix="_namepattern")
        nodes = self._nodes(spans)
        assert nodes
        span = nodes[0]
        op = span.attributes.get("db.operation.name", "")
        coll = span.attributes.get("db.collection.name", "")
        assert op in span.name
        if coll:
            assert coll in span.name

    def test_db_response_returned_rows_set_when_nonzero(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, results=[_make_result(rows_affected=500)], suffix="_rows")
        nodes = self._nodes(spans)
        assert nodes[0].attributes.get("db.response.returned_rows") == 500

    def test_db_response_status_code_set(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, results=[_make_result(status="success")], suffix="_statcode")
        nodes = self._nodes(spans)
        assert nodes[0].attributes.get("db.response.status_code") == "success"

    def test_db_query_summary_is_low_cardinality(self, exporter: InMemorySpanExporter) -> None:
        spans = self._spans(exporter, suffix="_summary")
        for span in spans:
            summary = span.attributes.get("db.query.summary", "")
            assert "test-invocation-abc123" not in summary


# ── Error / failure span tests ────────────────────────────────────────────────


class TestErrorSpans:
    @pytest.mark.parametrize("status", ["error", "fail", "runtime error"])
    def test_error_status_sets_error_type(self, status: str, exporter: InMemorySpanExporter) -> None:
        data = _make_run_results(results=[_make_result(status=status)])
        _emit_to_tmp(data, f"_err_{status.replace(' ', '_')}")
        spans = exporter.get_finished_spans()
        nodes = [s for s in spans if not s.name.startswith("dbt run")]
        assert nodes
        assert "error.type" in nodes[0].attributes

    @pytest.mark.parametrize("status", ["success", "warn", "skipped"])
    def test_non_error_status_omits_error_type(self, status: str, exporter: InMemorySpanExporter) -> None:
        data = _make_run_results(results=[_make_result(status=status)])
        _emit_to_tmp(data, f"_ok_{status}")
        spans = exporter.get_finished_spans()
        nodes = [s for s in spans if not s.name.startswith("dbt run")]
        for node in nodes:
            assert "error.type" not in node.attributes

    def test_error_span_has_failure_event(self, exporter: InMemorySpanExporter) -> None:
        result = _make_result(status="error")
        result["message"] = "Database connection timeout"
        data = _make_run_results(results=[result])
        _emit_to_tmp(data, "_failevt")
        spans = exporter.get_finished_spans()
        nodes = [s for s in spans if not s.name.startswith("dbt run")]
        event_names = [e.name for e in nodes[0].events]
        assert "dbt.failure" in event_names


# ── Multiple results tests ────────────────────────────────────────────────────


class TestMultipleResults:
    def test_one_span_per_result_plus_root(self, exporter: InMemorySpanExporter) -> None:
        results = [_make_result(name=f"model_{i}") for i in range(5)]
        data = _make_run_results(results=results)
        _emit_to_tmp(data, "_multi")
        spans = exporter.get_finished_spans()
        assert len(spans) == 6

    def test_empty_results_emits_only_root_span(self, exporter: InMemorySpanExporter) -> None:
        data = _make_run_results(results=[])
        tmp = Path("/tmp/empty_prr.json")
        tmp.write_text(json.dumps(data))
        names = parse_and_emit(tmp)
        assert len(names) == 1
        assert names[0].startswith("dbt run")

    def test_mixed_statuses_all_emitted(self, exporter: InMemorySpanExporter) -> None:
        results = [
            _make_result(name="success_model", status="success"),
            _make_result(name="failed_model", status="error"),
            _make_result(name="skipped_model", status="skipped"),
        ]
        data = _make_run_results(results=results)
        _emit_to_tmp(data, "_mixedstatus")
        spans = exporter.get_finished_spans()
        assert len(spans) == 4


# ── dbt Cloud poller semconv tests ────────────────────────────────────────────


class TestDbtCloudPollerSemconv:
    def _make_cloud_run(self, *, status: int = 10, status_humanized: str = "Success") -> dict[str, Any]:
        return {
            "id": 42,
            "job_id": 7,
            "status": status,
            "status_humanized": status_humanized,
            "environment_id": 3,
            "project_id": 1,
            "duration": 125.4,
            "duration_humanized": "2m 5s",
            "finished_at": "2024-03-01T11:00:00Z",
        }

    def test_poller_span_has_db_system_name(self, exporter: InMemorySpanExporter) -> None:
        DbtCloudPoller(account_id="123", api_token="token")._emit_run_span(self._make_cloud_run())
        spans = exporter.get_finished_spans()
        assert spans[0].attributes.get("db.system.name") == "other_sql"

    def test_poller_span_has_db_operation_name(self, exporter: InMemorySpanExporter) -> None:
        DbtCloudPoller(account_id="123", api_token="token")._emit_run_span(self._make_cloud_run())
        spans = exporter.get_finished_spans()
        assert spans[0].attributes.get("db.operation.name") == "dbt_cloud_run"

    def test_poller_span_kind_is_client(self, exporter: InMemorySpanExporter) -> None:
        DbtCloudPoller(account_id="123", api_token="token")._emit_run_span(self._make_cloud_run())
        spans = exporter.get_finished_spans()
        assert spans[0].kind == SpanKind.CLIENT

    def test_poller_error_run_sets_error_type(self, exporter: InMemorySpanExporter) -> None:
        DbtCloudPoller(account_id="123", api_token="token")._emit_run_span(
            self._make_cloud_run(status=20, status_humanized="Error")
        )
        spans = exporter.get_finished_spans()
        assert "error.type" in spans[0].attributes

    def test_poller_success_omits_error_type(self, exporter: InMemorySpanExporter) -> None:
        DbtCloudPoller(account_id="123", api_token="token")._emit_run_span(self._make_cloud_run())
        spans = exporter.get_finished_spans()
        assert "error.type" not in spans[0].attributes

    def test_poller_db_response_status_code_set(self, exporter: InMemorySpanExporter) -> None:
        DbtCloudPoller(account_id="123", api_token="token")._emit_run_span(self._make_cloud_run(status=10))
        spans = exporter.get_finished_spans()
        assert spans[0].attributes.get("db.response.status_code") == "10"

    def test_poller_namespace_from_env_name(self) -> None:
        assert DbtCloudPoller._resolve_namespace("Production Database") == "prod"
        assert DbtCloudPoller._resolve_namespace("Staging Environment") == "staging"
        assert DbtCloudPoller._resolve_namespace("Development") == "dev"
        assert DbtCloudPoller._resolve_namespace("") == ""

    def test_poll_once_deduplicates_seen_runs(self) -> None:
        poller = DbtCloudPoller(account_id="123", api_token="token")
        run = self._make_cloud_run()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [run]}
        mock_response.raise_for_status = lambda: None
        with patch("httpx.get", return_value=mock_response):
            first = poller.poll_once()
            second = poller.poll_once()
        assert len(first) == 1
        assert len(second) == 0


# ── File I/O tests ────────────────────────────────────────────────────────────


class TestFileIO:
    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_and_emit("/tmp/does_not_exist_dataobs_dbt.json")

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        with pytest.raises(json.JSONDecodeError):
            parse_and_emit(bad_file)

    def test_accepts_pathlib_path(self, exporter: InMemorySpanExporter) -> None:
        data = _make_run_results(results=[])
        tmp = Path("/tmp/test_pathlib_v2.json")
        tmp.write_text(json.dumps(data))
        names = parse_and_emit(Path(tmp))
        assert names

    def test_accepts_string_path(self, exporter: InMemorySpanExporter) -> None:
        data = _make_run_results(results=[])
        tmp = "/tmp/test_string_path_v2.json"
        Path(tmp).write_text(json.dumps(data))
        names = parse_and_emit(tmp)
        assert names
