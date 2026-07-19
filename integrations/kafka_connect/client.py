from urllib.parse import quote

from .config import KafkaConnectConfig
from .security import validate_endpoint


class KafkaConnectClient:
    """Read-only boundary. Transport is injected so credentials never enter browser/API responses."""

    def __init__(self, config: KafkaConnectConfig, transport):
        validate_endpoint(str(config.base_url), config.allowed_hosts)
        self.config = config
        self.transport = transport

    def connectors(self):
        return self.transport.get("/connectors", timeout=self.config.timeout_seconds)

    def status(self, name: str):
        return self.transport.get(f"/connectors/{quote(name, safe='')}/status", timeout=self.config.timeout_seconds)

    def connector_config(self, name: str):
        return self.transport.get(f"/connectors/{quote(name, safe='')}/config", timeout=self.config.timeout_seconds)

    def restart_failed_task(self, name: str, task_id: int, *, approved: bool):
        if not approved:
            raise PermissionError("approval required")
        return self.transport.post(
            f"/connectors/{quote(name, safe='')}/tasks/{task_id}/restart", timeout=self.config.timeout_seconds
        )
