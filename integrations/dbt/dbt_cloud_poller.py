"""
Poll dbt Cloud API for completed runs and emit OTel spans compliant with
the stable Database Semantic Conventions.

Spec: https://opentelemetry.io/docs/specs/semconv/db/database-spans/

Each dbt Cloud job run is modelled as a CLIENT span:
  - Root span: one per job run  (db.operation.name = "dbt_cloud_run")
  - Child spans: one per step/trigger (when step detail is available)

dbt Cloud does not expose a database system directly; we use "other_sql"
as the db.system.name value (semconv fallback for unrecognised SQL engines).

Resolves: https://github.com/Jagadeeshck/DataObs/issues/29
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

_tracer = trace.get_tracer("dataobs.dbt.cloud", "0.2.0")

DBT_CLOUD_BASE = "https://cloud.getdbt.com/api/v2"

# dbt Cloud job run status codes → OTel StatusCode
# https://docs.getdbt.com/dbt-cloud/api-v2#/operations/List%20Runs
_CLOUD_STATUS_TO_OTEL: dict[int, StatusCode] = {
    1: StatusCode.UNSET,    # Queued
    2: StatusCode.UNSET,    # Starting
    3: StatusCode.UNSET,    # Running
    10: StatusCode.OK,      # Success
    20: StatusCode.ERROR,   # Error
    30: StatusCode.ERROR,   # Cancelled
}

# Human-readable status values that indicate failure
_ERROR_STATUS_HUMANIZED = frozenset({"Error", "Cancelled"})

# dbt Cloud environment type → db.namespace (low-cardinality)
_ENV_TYPE_TO_NAMESPACE: dict[str, str] = {
    "development": "dev",
    "staging": "staging",
    "production": "prod",
}


class DbtCloudPoller:
    """
    Polls dbt Cloud for completed job runs and emits semconv-compliant OTel spans.

    Args:
        account_id: dbt Cloud numeric account ID.
        api_token: dbt Cloud service token or personal API token.
        poll_interval_seconds: Polling cadence. Default 60 s.
        base_url: Override for on-prem / single-tenant dbt Cloud.
    """

    def __init__(
        self,
        account_id: str,
        api_token: str,
        poll_interval_seconds: int = 60,
        base_url: str = DBT_CLOUD_BASE,
    ) -> None:
        self._account_id = str(account_id)
        self._headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }
        self._poll_interval = poll_interval_seconds
        self._base_url = base_url.rstrip("/")
        self._seen_runs: set[int] = set()

    # ── Public API ────────────────────────────────────────────────────────────

    def poll_once(self) -> list[dict[str, Any]]:
        """
        Fetch the latest completed runs and emit a span for each new one.

        Returns:
            List of new run dicts that were processed this call.
        """
        url = f"{self._base_url}/accounts/{self._account_id}/runs/"
        resp = httpx.get(
            url,
            headers=self._headers,
            params={
                "status": 10,       # 10 = Success; caller can widen to include Error (20)
                "order_by": "-id",
                "limit": 50,
            },
            timeout=30.0,
        )
        resp.raise_for_status()

        runs: list[dict[str, Any]] = resp.json().get("data", []) or []
        new_runs = [r for r in runs if r.get("id") not in self._seen_runs]

        for run in new_runs:
            run_id = run.get("id")
            if run_id is not None:
                self._seen_runs.add(run_id)
            self._emit_run_span(run)

        return new_runs

    def run_forever(self) -> None:
        """Block indefinitely, polling every ``poll_interval_seconds``."""
        while True:
            try:
                self.poll_once()
            except httpx.HTTPStatusError as exc:
                # Log but don't crash on transient API errors
                _tracer.start_as_current_span("dbt.cloud.poll_error").__enter__()
                print(f"[dbt-cloud-poller] HTTP error {exc.response.status_code}: {exc}")
            except Exception as exc:
                print(f"[dbt-cloud-poller] unexpected error: {exc}")
            time.sleep(self._poll_interval)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _emit_run_span(self, run: dict[str, Any]) -> None:
        """Emit one CLIENT span for a dbt Cloud job run."""
        status_code: int = run.get("status", 0)
        status_humanized: str = run.get("status_humanized", "Unknown")
        job_id: int = run.get("job_id", 0)
        run_id: int = run.get("id", 0)
        env_id: int = run.get("environment_id", 0)
        project_id: int = run.get("project_id", 0)
        duration_humanized: str = run.get("duration_humanized", "")
        duration_seconds: float = run.get("duration", 0.0) or 0.0
        finished_at: str = run.get("finished_at") or ""

        # ── Semconv attributes ─────────────────────────────────────────────────
        # db.system.name: dbt Cloud targets SQL databases, use "other_sql"
        # as the semconv fallback since dbt Cloud itself is not a DBMS.
        db_system_name = "other_sql"

        # db.operation.name: the high-level operation dbt Cloud is performing
        db_operation_name = "dbt_cloud_run"

        # db.namespace: map environment name to low-cardinality namespace
        env_name: str = run.get("environment", {}).get("name", "") if isinstance(
            run.get("environment"), dict
        ) else ""
        db_namespace = self._resolve_namespace(env_name)

        # db.query.summary: low-cardinality summary
        job_name: str = run.get("job", {}).get("name", f"job-{job_id}") if isinstance(
            run.get("job"), dict
        ) else f"job-{job_id}"
        db_query_summary = f"dbt_cloud_run {job_name}"

        # db.response.status_code: use dbt Cloud's integer status code as string
        db_response_status_code = str(status_code) if status_code else None

        # OTel span status
        otel_status_code = _CLOUD_STATUS_TO_OTEL.get(status_code, StatusCode.UNSET)
        is_error = status_humanized in _ERROR_STATUS_HUMANIZED

        # ── Span name ──────────────────────────────────────────────────────────
        # Pattern: "{db.operation.name} {db.namespace}" per semconv naming spec.
        span_name = f"{db_operation_name} {db_namespace}" if db_namespace else db_operation_name

        attrs: dict[str, Any] = {
            # --- Stable DB semconv ---
            "db.system.name": db_system_name,
            "db.operation.name": db_operation_name,
            "db.query.summary": db_query_summary,
        }
        if db_namespace:
            attrs["db.namespace"] = db_namespace
        if db_response_status_code:
            attrs["db.response.status_code"] = db_response_status_code
        if is_error:
            attrs["error.type"] = f"dbt.cloud.{status_humanized.lower()}"

        # --- dbt Cloud–specific custom attributes ---
        attrs.update({
            "dbt.cloud.account_id": self._account_id,
            "dbt.cloud.job_id": str(job_id),
            "dbt.cloud.run_id": str(run_id),
            "dbt.cloud.environment_id": str(env_id),
            "dbt.cloud.project_id": str(project_id),
            "dbt.cloud.status": status_humanized,
            "dbt.cloud.status_code": status_code,
            "dbt.cloud.job_name": job_name,
            "dbt.cloud.duration_humanized": duration_humanized,
            "dbt.cloud.duration_seconds": duration_seconds,
            "dbt.cloud.finished_at": finished_at,
            "dbt.cloud.run_url": (
                f"https://cloud.getdbt.com/deploy/{project_id}/runs/{run_id}"
                if project_id and run_id else ""
            ),
        })

        with _tracer.start_as_current_span(
            span_name,
            kind=SpanKind.CLIENT,
            attributes=attrs,
        ) as span:
            span.set_status(Status(otel_status_code))

            if is_error:
                error_msg = run.get("trigger", {}).get("cause", "") if isinstance(
                    run.get("trigger"), dict
                ) else ""
                span.add_event(
                    "dbt.cloud.run_failed",
                    attributes={
                        "dbt.cloud.status": status_humanized,
                        "message": error_msg[:1024] if error_msg else f"dbt Cloud run {run_id} {status_humanized}",
                    },
                )
                if error_msg:
                    span.record_exception(
                        RuntimeError(f"dbt Cloud run {run_id} failed: {error_msg}")
                    )

    @staticmethod
    def _resolve_namespace(env_name: str) -> str:
        """Map dbt Cloud environment name to a low-cardinality db.namespace."""
        if not env_name:
            return ""
        lower = env_name.lower()
        for key, val in _ENV_TYPE_TO_NAMESPACE.items():
            if key in lower:
                return val
        # Use the first word of the env name, lowercased, as a fallback
        return lower.split()[0] if lower.split() else lower
