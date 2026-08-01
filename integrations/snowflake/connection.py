from __future__ import annotations

import importlib
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from .configuration import SnowflakeConfiguration
from .credentials import CredentialResolver
from .errors import map_connector_error, safe_error


class SnowflakeConnectionFactory:
    def __init__(self, resolver: CredentialResolver | None = None, connector: Any = None) -> None:
        self.resolver = resolver or CredentialResolver()
        self.connector = connector

    def _connector(self) -> Any:
        if self.connector is not None:
            return self.connector
        try:
            return importlib.import_module("snowflake.connector")
        except ImportError as exc:
            raise safe_error("dependency_unavailable") from exc

    @contextmanager
    def connect(self, cfg: SnowflakeConfiguration, query_tag: str) -> Iterator[Any]:
        kwargs: dict[str, Any] = {
            "account": cfg.account_identifier,
            "user": cfg.user,
            "role": cfg.role,
            "login_timeout": cfg.network_timeout_seconds,
            "network_timeout": cfg.network_timeout_seconds,
            "session_parameters": {
                "TIMEZONE": "UTC",
                "STATEMENT_TIMEOUT_IN_SECONDS": cfg.statement_timeout_seconds,
                "QUERY_TAG": query_tag[:128],
            },
        }
        if cfg.collector_warehouse:
            kwargs["warehouse"] = cfg.collector_warehouse
        auth = cfg.authentication
        if auth.type == "key_pair":
            kwargs["private_key"] = self.resolver.resolve(auth.secret_ref or "")
            if auth.passphrase_ref:
                kwargs["private_key_passphrase"] = self.resolver.resolve(auth.passphrase_ref)
        elif auth.type == "oauth":
            kwargs.update(authenticator="oauth", token=self.resolver.resolve(auth.secret_ref or ""))
        else:
            kwargs.update(authenticator="WORKLOAD_IDENTITY", workload_identity_provider=auth.identity_provider)
        connection = None
        try:
            connection = self._connector().connect(**kwargs)
            yield connection
        except Exception as exc:
            if getattr(exc, "code", None) in {"dependency_unavailable", "credential_unavailable"}:
                raise
            raise map_connector_error(exc) from None
        finally:
            kwargs.clear()
            if connection is not None:
                connection.close()
