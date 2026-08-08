from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from .configuration import KibanaConfiguration
from .errors import KibanaError, KibanaOutcomeUnknown

_SAFE_METHODS = {"GET", "HEAD"}


def _segment(value: str) -> str:
    if not value or len(value) > 256 or value in {".", ".."}:
        raise ValueError("invalid Kibana resource identifier")
    return quote(value, safe="")


class KibanaClient:
    """Private transport used only through explicit, allowlisted product methods."""

    def __init__(self, configuration: KibanaConfiguration, session: requests.Session | None = None) -> None:
        self.configuration = configuration
        self._session = session or requests.Session()

    def _path(self, space: str, path: str) -> str:
        if not path.startswith("/api/") or "//" in path or ".." in path:
            raise ValueError("invalid Kibana API path")
        prefix = "" if space == "default" else f"/s/{_segment(space)}"
        return f"{self.configuration.base_url.rstrip('/')}{prefix}{path}"

    def _send(
        self,
        method: str,
        space: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        method = method.upper()
        headers = {"accept": "application/json"}
        if method not in _SAFE_METHODS:
            headers["kbn-xsrf"] = "dataobs"
            headers["content-type"] = "application/json"
        if self.configuration.api_key:
            headers["authorization"] = f"ApiKey {self.configuration.api_key}"
        if request_id:
            headers["x-opaque-id"] = request_id[:128]
        try:
            response = self._session.request(
                method,
                self._path(space, path),
                json=body,
                params=params,
                headers=headers,
                timeout=(self.configuration.connect_timeout, self.configuration.read_timeout),
                allow_redirects=False,
                verify=True,
                stream=True,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            error = KibanaOutcomeUnknown if method not in _SAFE_METHODS else KibanaError
            raise error("kibana_unreachable") from exc
        if 300 <= response.status_code < 400:
            raise KibanaError("kibana_redirect_rejected", response.status_code)
        if response.status_code >= 400:
            code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict", 429: "rate_limited"}.get(
                response.status_code, "provider_error"
            )
            raise KibanaError(code, response.status_code)
        content = bytearray()
        for chunk in response.iter_content(16_384):
            content.extend(chunk)
            if len(content) > self.configuration.max_response_bytes:
                raise KibanaError("response_too_large")
        if not content:
            return {}
        try:
            value = response.json()
        except ValueError as exc:
            raise KibanaError("invalid_provider_response") from exc
        if not isinstance(value, dict):
            raise KibanaError("invalid_provider_response")
        return value

    # Elastic Workflows GA API, Kibana 9.4.
    def create_workflow(self, space: str, definition: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        return self._send("POST", space, "/api/workflows/workflow", body=definition, request_id=request_id)

    def get_workflow(self, space: str, workflow_id: str) -> dict[str, Any]:
        return self._send("GET", space, f"/api/workflows/workflow/{_segment(workflow_id)}")

    def update_workflow(self, space: str, workflow_id: str, definition: dict[str, Any]) -> dict[str, Any]:
        return self._send("PUT", space, f"/api/workflows/workflow/{_segment(workflow_id)}", body=definition)

    def run_workflow(self, space: str, workflow_id: str, inputs: dict[str, Any], request_id: str) -> dict[str, Any]:
        return self._send(
            "POST",
            space,
            f"/api/workflows/workflow/{_segment(workflow_id)}/run",
            body={"inputs": inputs},
            request_id=request_id,
        )

    def get_workflow_execution(self, space: str, execution_id: str) -> dict[str, Any]:
        return self._send(
            "GET",
            space,
            f"/api/workflows/executions/{_segment(execution_id)}",
            params={"includeInput": "false", "includeOutput": "false"},
        )

    def list_workflow_executions(self, space: str, workflow_id: str) -> dict[str, Any]:
        return self._send("GET", space, f"/api/workflows/workflow/{_segment(workflow_id)}/executions")

    # Cases API remains independent from Workflows.
    def create_case(self, space: str, body: dict[str, Any], request_id: str) -> dict[str, Any]:
        return self._send("POST", space, "/api/cases", body=body, request_id=request_id)

    def get_case(self, space: str, case_id: str) -> dict[str, Any]:
        return self._send("GET", space, f"/api/cases/{_segment(case_id)}")

    def add_case_comment(self, space: str, case_id: str, body: dict[str, Any], request_id: str) -> dict[str, Any]:
        return self._send("POST", space, f"/api/cases/{_segment(case_id)}/comments", body=body, request_id=request_id)
