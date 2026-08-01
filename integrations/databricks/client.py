from __future__ import annotations

import importlib
import importlib.metadata
from dataclasses import dataclass

from .authentication import resolve_secret
from .errors import safe_error

READ_ALLOWLIST = frozenset(
    {
        "workspace.get_status",
        "catalogs.list",
        "schemas.list",
        "tables.list",
        "tables.get",
        "volumes.list",
        "warehouses.list",
        "warehouses.get",
        "jobs.list",
        "jobs.get",
        "jobs.list_runs",
        "jobs.get_run",
        "statement_execution.execute_statement",
        "statement_execution.get_statement",
        "statement_execution.cancel_execution",
    }
)


@dataclass
class DatabricksClientFactory:
    injected_client: object | None = None

    def create(self, cfg):
        if self.injected_client is not None:
            return self.injected_client
        try:
            module = importlib.import_module("databricks.sdk")
        except ImportError as exc:
            raise safe_error("dependency_unavailable") from exc
        kwargs = {"host": cfg.workspace_host, "auth_type": "oauth-m2m"}
        if cfg.authentication.type == "oauth_m2m":
            kwargs.update(
                client_id=resolve_secret(cfg.authentication.client_id_ref),
                client_secret=resolve_secret(cfg.authentication.client_secret_ref),
            )
        else:
            kwargs.update(token=resolve_secret(cfg.authentication.token_ref), auth_type="pat")
        return module.WorkspaceClient(**kwargs)

    @staticmethod
    def sdk_version() -> str:
        try:
            return importlib.metadata.version("databricks-sdk")
        except importlib.metadata.PackageNotFoundError:
            return "unavailable"

    @staticmethod
    def close(client: object) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()
