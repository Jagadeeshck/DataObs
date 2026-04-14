"""
Poll dbt Cloud API for completed runs and emit OTel spans.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/29
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx
from opentelemetry import trace

_tracer = trace.get_tracer("dataobs.dbt.cloud")

DBT_CLOUD_BASE = "https://cloud.getdbt.com/api/v2"


class DbtCloudPoller:
    """
    Polls dbt Cloud for completed job runs and emits OTel spans.

    Args:
        account_id: dbt Cloud account ID.
        api_token: dbt Cloud API token.
        poll_interval_seconds: How often to poll for new runs.
    """

    def __init__(
        self,
        account_id: str,
        api_token: str,
        poll_interval_seconds: int = 60,
    ) -> None:
        self._account_id = account_id
        self._headers = {"Authorization": f"Token {api_token}"}
        self._poll_interval = poll_interval_seconds
        self._seen_runs: set[int] = set()

    def poll_once(self) -> list[dict[str, Any]]:
        url = f"{DBT_CLOUD_BASE}/accounts/{self._account_id}/runs/"
        resp = httpx.get(url, headers=self._headers, params={"status": 10, "limit": 50})
        resp.raise_for_status()
        runs = resp.json().get("data", [])
        new_runs = [r for r in runs if r["id"] not in self._seen_runs]
        for run in new_runs:
            self._seen_runs.add(run["id"])
            self._emit_run_span(run)
        return new_runs

    def _emit_run_span(self, run: dict[str, Any]) -> None:
        with _tracer.start_as_current_span(
            "dbt.cloud.run",
            attributes={
                "dbt.job.id": run.get("job_id", 0),
                "dbt.run.id": run.get("id", 0),
                "dbt.account.id": self._account_id,
                "dbt.status": run.get("status_humanized", ""),
                "dbt.environment.id": run.get("environment_id", 0),
                "dbt.duration_seconds": run.get("duration_humanized", ""),
            },
        ):
            pass

    def run_forever(self) -> None:
        while True:
            try:
                self.poll_once()
            except Exception as exc:
                print(f"[dbt-cloud-poller] error: {exc}")
            time.sleep(self._poll_interval)
