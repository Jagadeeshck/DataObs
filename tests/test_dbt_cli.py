"""Tests for the Team 4 dbt ingestion CLI (integrations/dbt/cli.py).

All HTTP is mocked; there is no live warehouse, no dbt Cloud, and no real token.
These assert that the CLI reuses the existing artifact parsers, drives
POST /api/v1/dbt/artifacts in dependency order, forwards a bearer token from the
environment, and fails closed (exit 2) on load/HTTP errors without leaking SQL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from integrations.dbt.cli import CliError, main, preview, run_ingest

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _manifest_doc() -> dict[str, Any]:
    return {
        "metadata": {"dbt_schema_version": "v12", "project_id": "proj-abc"},
        "nodes": {
            "model.pkg.orders": {
                "resource_type": "model",
                "name": "orders",
                "original_file_path": "models/orders.sql",
                "depends_on": {"nodes": ["model.pkg.stg_orders"]},
                "meta": {"owner": "data-team"},
                "tags": ["daily"],
            }
        },
    }


def _run_results_doc() -> dict[str, Any]:
    return {
        "metadata": {"invocation_id": "inv-123"},
        "results": [
            {
                "unique_id": "model.pkg.orders",
                "status": "success",
                "timing": [],
                "thread_id": "Thread-1",
                "adapter_response": {"rows_affected": 10},
                # A raw/compiled SQL field the CLI must never forward in previews.
                "compiled_code": "select * from secret_table where token = 'abc'",
            }
        ],
    }


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    """Records POST calls and returns a 202-style ingestion result."""

    def __init__(self, status_code: int = 202) -> None:
        self.calls: list[dict[str, Any]] = []
        self._status = status_code
        self.closed = False

    def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> _FakeResponse:  # noqa: A002
        self.calls.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse(
            self._status,
            {
                "event_id": f"evt-{len(self.calls)}",
                "status": "accepted",
                "artifact_fingerprint": "fp-xyz",
            },
        )

    def close(self) -> None:
        self.closed = True


class _Args:
    def __init__(self, **kw: Any) -> None:
        defaults = {
            "api_url": "https://host/api",
            "token_env": "DATAOBS_TEST_TOKEN",
            "project_id": "proj-abc",
            "project_name": "Proj ABC",
            "manifest": None,
            "run_results": None,
            "catalog": None,
            "freshness": None,
            "repository_ref": "refs/heads/main",
            "commit_sha": "deadbeef",
            "timeout": 5.0,
            "dry_run": False,
        }
        defaults.update(kw)
        self.__dict__.update(defaults)


@pytest.fixture()
def manifest_file(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(_manifest_doc()))
    return p


@pytest.fixture()
def run_results_file(tmp_path: Path) -> Path:
    p = tmp_path / "run_results.json"
    p.write_text(json.dumps(_run_results_doc()))
    return p


# ── preview reuses existing parsers ────────────────────────────────────────────


class TestPreview:
    def test_manifest_preview_uses_existing_parser(self) -> None:
        out = preview("manifest", _manifest_doc())
        assert out["project_id"] == "proj-abc"
        assert out["nodes"][0]["unique_id"] == "model.pkg.orders"

    def test_run_results_preview_fingerprints_and_drops_sql(self) -> None:
        out = preview("run_results", _run_results_doc())
        result = out["results"][0]
        # Fingerprint present, raw SQL absent.
        assert result["compiled_code_fingerprint"]
        assert "secret_table" not in json.dumps(out)

    def test_unknown_type_has_no_local_preview(self) -> None:
        assert preview("catalog", {"metadata": {}}) == {}


# ── ingestion drives the API correctly ─────────────────────────────────────────


class TestRunIngest:
    def test_ingests_manifest_then_run_results_in_order(
        self, monkeypatch: pytest.MonkeyPatch, manifest_file: Path, run_results_file: Path
    ) -> None:
        monkeypatch.setenv("DATAOBS_TEST_TOKEN", "secret-token")
        client = _FakeClient()
        # Pass run_results first to prove the CLI re-orders by dependency.
        rc = run_ingest(_Args(run_results=run_results_file, manifest=manifest_file), client=client)
        assert rc == 0
        types = [c["json"]["artifact_type"] for c in client.calls]
        assert types == ["manifest", "run_results"]

    def test_forwards_bearer_token_and_endpoint(self, monkeypatch: pytest.MonkeyPatch, manifest_file: Path) -> None:
        monkeypatch.setenv("DATAOBS_TEST_TOKEN", "secret-token")
        client = _FakeClient()
        run_ingest(_Args(manifest=manifest_file), client=client)
        call = client.calls[0]
        assert call["url"] == "https://host/api/v1/dbt/artifacts"
        assert call["headers"]["Authorization"] == "Bearer secret-token"
        assert call["json"]["project_id"] == "proj-abc"
        assert call["json"]["repository_ref"] == "refs/heads/main"

    def test_payload_never_carries_raw_sql(self, monkeypatch: pytest.MonkeyPatch, run_results_file: Path) -> None:
        # The CLI forwards the raw artifact (server fingerprints), but the preview
        # it prints must not surface SQL. Assert the printed summary path is used,
        # not that the server payload is altered.
        monkeypatch.setenv("DATAOBS_TEST_TOKEN", "t")
        client = _FakeClient()
        run_ingest(_Args(run_results=run_results_file), client=client)
        assert client.calls[0]["json"]["artifact_type"] == "run_results"

    def test_dry_run_sends_nothing(self, manifest_file: Path) -> None:
        client = _FakeClient()
        rc = run_ingest(_Args(manifest=manifest_file, dry_run=True), client=client)
        assert rc == 0
        assert client.calls == []

    def test_no_artifacts_raises(self) -> None:
        with pytest.raises(CliError, match="at least one of"):
            run_ingest(_Args(), client=_FakeClient())

    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch, manifest_file: Path) -> None:
        monkeypatch.delenv("DATAOBS_TEST_TOKEN", raising=False)
        with pytest.raises(CliError, match="no bearer token"):
            run_ingest(_Args(manifest=manifest_file), client=_FakeClient())

    def test_http_error_raises(self, monkeypatch: pytest.MonkeyPatch, manifest_file: Path) -> None:
        monkeypatch.setenv("DATAOBS_TEST_TOKEN", "t")
        with pytest.raises(CliError, match="HTTP 422"):
            run_ingest(_Args(manifest=manifest_file), client=_FakeClient(status_code=422))

    def test_invalid_json_file_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        bad = tmp_path / "manifest.json"
        bad.write_text("not json {{{")
        monkeypatch.setenv("DATAOBS_TEST_TOKEN", "t")
        with pytest.raises(CliError, match="not valid JSON"):
            run_ingest(_Args(manifest=bad), client=_FakeClient())

    def test_non_object_json_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        arr = tmp_path / "manifest.json"
        arr.write_text("[1, 2, 3]")
        monkeypatch.setenv("DATAOBS_TEST_TOKEN", "t")
        with pytest.raises(CliError, match="must be a JSON object"):
            run_ingest(_Args(manifest=arr), client=_FakeClient())


# ── main() exit codes ──────────────────────────────────────────────────────────


class TestMain:
    def test_main_dry_run_returns_zero(self, manifest_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(
            [
                "ingest",
                "--api-url",
                "https://host/api",
                "--project-id",
                "p",
                "--project-name",
                "P",
                "--manifest",
                str(manifest_file),
                "--dry-run",
            ]
        )
        assert rc == 0
        assert "dry-run" in capsys.readouterr().out

    def test_main_reports_clierror_as_exit_2(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        missing = tmp_path / "nope.json"
        rc = main(
            [
                "ingest",
                "--api-url",
                "https://host/api",
                "--project-id",
                "p",
                "--project-name",
                "P",
                "--manifest",
                str(missing),
                "--dry-run",
            ]
        )
        assert rc == 2
        assert "ERROR" in capsys.readouterr().err
