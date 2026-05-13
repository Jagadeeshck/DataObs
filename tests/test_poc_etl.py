"""
tests/test_poc_etl.py
─────────────────────
Unit tests for src/poc/etl.py:
  - CSV / JSON / XLSX parsing
  - Field-name sanitisation
  - Type inference
  - Mapping generation
  - Envelope enrichment
  - Integration smoke: DatasetETL.ingest_source() with mocked ES + HTTP
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


def _make_csv(rows: List[Dict[str, str]], headers: List[str] = None) -> bytes:
    buf = io.StringIO()
    hdrs = headers or list(rows[0].keys())
    w = csv.DictWriter(buf, fieldnames=hdrs)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode()


def _make_json(records: List[Dict]) -> bytes:
    return json.dumps(records).encode()


class TestSafeField:
    def test_strips_whitespace(self):
        from src.poc.etl import _safe_field
        assert _safe_field("  column name  ") == "column_name"

    def test_special_chars_replaced(self):
        from src.poc.etl import _safe_field
        assert _safe_field("Road (Category)") == "road_category"

    def test_already_clean(self):
        from src.poc.etl import _safe_field
        assert _safe_field("accident_index") == "accident_index"

    def test_empty_returns_field(self):
        from src.poc.etl import _safe_field
        assert _safe_field("") == "field"
        assert _safe_field("---") == "field"


class TestInferType:
    def test_date_iso(self):
        from src.poc.etl import _infer_type
        assert _infer_type(["2023-01-01", "2023-06-15"]) == "date"

    def test_date_uk_slash(self):
        from src.poc.etl import _infer_type
        assert _infer_type(["01/01/2023", "15/06/2023"]) == "date"

    def test_integer(self):
        from src.poc.etl import _infer_type
        assert _infer_type(["1", "42", "-7", "1000"]) == "long"

    def test_float(self):
        from src.poc.etl import _infer_type
        assert _infer_type(["1.5", "42.0", "-7.3"]) == "double"

    def test_keyword_short(self):
        from src.poc.etl import _infer_type
        assert _infer_type(["England", "Wales", "Scotland"]) == "keyword"

    def test_empty_values(self):
        from src.poc.etl import _infer_type
        assert _infer_type(["", "", ""]) == "keyword"


class TestInferMapping:
    def test_envelope_fields_always_present(self):
        from src.poc.etl import _infer_mapping
        rows = [{"accident_index": "2023-001", "number_of_casualties": "1"}]
        props = _infer_mapping(rows)
        assert props["@timestamp"]["type"] == "date"
        assert props["run_id"]["type"] == "keyword"
        assert props["dataset"]["type"] == "keyword"

    def test_infers_long_for_integer_column(self):
        from src.poc.etl import _infer_mapping
        rows = [{"count": str(i)} for i in range(50)]
        props = _infer_mapping(rows)
        assert props["count"]["type"] == "long"

    def test_empty_rows(self):
        from src.poc.etl import _infer_mapping
        assert _infer_mapping([]) == {}


class TestParseDataset:
    def test_csv_basic(self):
        from src.poc.etl import parse_dataset
        raw = _make_csv([{"accident_index": "001", "severity": "Serious"}])
        hdrs, rows = parse_dataset(raw, "csv")
        assert "accident_index" in hdrs
        assert rows[0]["accident_index"] == "001"

    def test_csv_header_sanitised(self):
        from src.poc.etl import parse_dataset
        raw = _make_csv([{"Road Type (Local)": "A Road"}], headers=["Road Type (Local)"])
        hdrs, rows = parse_dataset(raw, "csv")
        assert "road_type_local" in hdrs

    def test_json_list(self):
        from src.poc.etl import parse_dataset
        raw = _make_json([{"site_id": "1", "name": "London"}, {"site_id": "2", "name": "Leeds"}])
        hdrs, rows = parse_dataset(raw, "json")
        assert len(rows) == 2
        assert "site_id" in hdrs

    def test_json_wrapped(self):
        from src.poc.etl import parse_dataset
        raw = json.dumps({"data": [{"id": 1}]}).encode()
        _, rows = parse_dataset(raw, "json")
        assert rows[0]["id"] == 1

    def test_max_rows_truncation(self):
        from src.poc.etl import parse_dataset
        data = [{"n": str(i)} for i in range(200)]
        raw = _make_csv(data)
        _, rows = parse_dataset(raw, "csv", max_rows=50)
        assert len(rows) == 50

    def test_unknown_format_falls_back_to_csv(self):
        from src.poc.etl import parse_dataset
        raw = _make_csv([{"x": "1"}])
        _, rows = parse_dataset(raw, "tsv")
        assert rows[0]["x"] == "1"


class TestEnrich:
    def test_envelope_fields_added(self):
        from src.poc.etl import _enrich
        rows = [{"accident_index": "001"}]
        docs = list(_enrich(rows, dataset="road-safety", run_id="RUN1",
                            theme="transport", source_url="http://x", ts="2025-01-01T00:00:00Z"))
        assert docs[0]["@timestamp"] == "2025-01-01T00:00:00Z"
        assert docs[0]["dataset"] == "road-safety"
        assert docs[0]["run_id"] == "RUN1"
        assert docs[0]["row_index"] == 0
        assert docs[0]["accident_index"] == "001"


class TestDatasetETLIngestSource:
    def _make_etl(self):
        from src.poc.etl import DatasetETL
        etl = DatasetETL(es_host="http://mock:9200")
        etl.es = MagicMock()
        etl.es.indices.exists.return_value = True
        return etl

    def test_happy_path_csv(self):
        etl = self._make_etl()
        csv_bytes = _make_csv([{"col_a": "1", "col_b": "hello"} for _ in range(10)])
        with patch("src.poc.etl._download", return_value=csv_bytes):
            with patch("src.poc.etl.bulk_index", return_value=10) as mock_bulk:
                result = etl.ingest_source(
                    {"name": "test-ds", "resource_url": "http://x/test.csv",
                     "format": "csv", "theme": "test"},
                    run_id="RUN1",
                )
        assert result["status"] == "ok"
        assert result["rows_ingested"] == 10
        assert result["dataset"] == "test-ds"
        assert result["index"] == "dataobs-raw-test-ds"
        mock_bulk.assert_called_once()

    def test_download_failure_returns_error_status(self):
        etl = self._make_etl()
        with patch("src.poc.etl._download", side_effect=Exception("connection refused")):
            result = etl.ingest_source(
                {"name": "fail-ds", "resource_url": "http://bad/x.csv",
                 "format": "csv", "theme": "test"},
                run_id="RUN2",
            )
        assert result["status"] == "error"
        assert "connection refused" in result["error"]
        assert result["rows_ingested"] == 0

    def test_empty_dataset_returns_empty_status(self):
        etl = self._make_etl()
        with patch("src.poc.etl._download", return_value=b"col_a\n"):
            result = etl.ingest_source(
                {"name": "empty-ds", "resource_url": "http://x/empty.csv",
                 "format": "csv", "theme": "test"},
                run_id="RUN3",
            )
        assert result["status"] == "empty"
        assert result["rows_ingested"] == 0

    def test_no_otel_collector_reference_in_logs(self, caplog):
        import logging
        etl = self._make_etl()
        csv_bytes = _make_csv([{"x": "1"}])
        with patch("src.poc.etl._download", return_value=csv_bytes):
            with patch("src.poc.etl.bulk_index", return_value=1):
                with caplog.at_level(logging.DEBUG, logger="src.poc.etl"):
                    etl.ingest_source(
                        {"name": "ds", "resource_url": "http://x.csv",
                         "format": "csv", "theme": "t"},
                        run_id="R",
                    )
        assert "otel-collector" not in caplog.text.lower()
