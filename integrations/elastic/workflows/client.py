from __future__ import annotations

from typing import Any

from integrations.elastic.kibana import KibanaClient, KibanaConfiguration

from .models import KibanaAuth


class KibanaWorkflowClient:
    """Compatibility facade over the shared bounded Kibana transport."""

    def __init__(self, auth: KibanaAuth, timeout: int = 30) -> None:
        self.auth = auth
        self._client = KibanaClient(
            KibanaConfiguration(
                auth.base_url,
                auth.api_key,
                {"configured": auth.space},
                production=auth.base_url.startswith("https://"),
                read_timeout=float(timeout),
            )
        )

    @property
    def space(self) -> str:
        return self.auth.space

    def create_workflow(self, definition: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        return self._client.create_workflow(self.space, definition, request_id)

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self._client.get_workflow(self.space, workflow_id)

    def update_workflow(self, workflow_id: str, definition: dict[str, Any]) -> dict[str, Any]:
        return self._client.update_workflow(self.space, workflow_id, definition)

    def run_workflow(
        self, workflow_id: str, inputs: dict[str, Any] | None = None, request_id: str = "dataobs"
    ) -> dict[str, Any]:
        return self._client.run_workflow(self.space, workflow_id, inputs or {}, request_id)

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        return self._client.get_workflow_execution(self.space, execution_id)

    def list_executions(self, workflow_id: str) -> dict[str, Any]:
        return self._client.list_workflow_executions(self.space, workflow_id)
