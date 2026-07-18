from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import requests

from .models import KibanaAuth


class KibanaWorkflowClient:
    def __init__(self, auth: KibanaAuth, timeout: int = 30) -> None:
        self.auth = auth
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "KibanaWorkflowClient":
        return cls(KibanaAuth(os.getenv("KIBANA_URL", "http://localhost:5601"), os.getenv("KIBANA_API_KEY")))

    def _headers(self) -> dict[str, str]:
        headers = {"kbn-xsrf": "dataobs", "content-type": "application/json"}
        if self.auth.api_key:
            headers["Authorization"] = f"ApiKey {self.auth.api_key}"
        return headers

    def _url(self, path: str) -> str:
        prefix = f"/s/{self.auth.space}" if self.auth.space != "default" else ""
        return urljoin(self.auth.base_url.rstrip("/") + "/", (prefix + path).lstrip("/"))

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        auth = None if self.auth.api_key else (self.auth.username, self.auth.password)
        response = requests.request(
            method, self._url(path), headers=self._headers(), auth=auth, timeout=self.timeout, **kwargs
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Kibana workflow API error {response.status_code}: {response.text[:300]}")
        return response.json() if response.content else {}

    def list_workflows(self) -> dict[str, Any]:
        return self.request("GET", "/api/workflows")

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/workflows/{workflow_id}")

    def import_workflow(self, yaml_text: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/api/workflows/import",
            data=yaml_text,
            headers={**self._headers(), "content-type": "application/yaml"},
        )

    def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", f"/api/workflows/{workflow_id}/run", json={"inputs": inputs or {}})

    def get_execution(self, workflow_id: str, execution_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/workflows/{workflow_id}/executions/{execution_id}")

    def list_executions(self, workflow_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/workflows/{workflow_id}/executions")

    def cancel_execution(self, workflow_id: str, execution_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/workflows/{workflow_id}/executions/{execution_id}/cancel")

    def resume_execution(self, workflow_id: str, execution_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return self.request(
            "POST", f"/api/workflows/{workflow_id}/executions/{execution_id}/resume", json={"inputs": inputs}
        )
