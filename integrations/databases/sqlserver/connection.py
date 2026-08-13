from __future__ import annotations

from contextlib import contextmanager

from .authentication import authentication_options
from .errors import SqlServerCollectorError


def build_connection_string(cfg) -> str:
    options = {
        "Server": f"{cfg.host},{cfg.port}",
        "Database": cfg.database,
        "Encrypt": "Strict" if cfg.tls.get("mode", "strict") == "strict" else "Mandatory",
        "TrustServerCertificate": "no",
        "Connection Timeout": str(cfg.limits["connection_timeout_seconds"]),
        **authentication_options(cfg),
    }
    if cfg.tls.get("hostname_in_certificate"):
        options["HostnameInCertificate"] = cfg.tls["hostname_in_certificate"]
    return ";".join(f"{key}={{{str(value).replace('}', '}}')}}}" for key, value in options.items())


class SqlServerConnectionFactory:
    @contextmanager
    def connect(self, cfg):
        try:
            import mssql_python
        except ImportError as exc:
            raise SqlServerCollectorError("dependency_unavailable") from exc
        mssql_python.pooling(enabled=False)
        connection = mssql_python.connect(build_connection_string(cfg), autocommit=True)
        connection.timeout = cfg.limits["query_timeout_seconds"]
        try:
            yield connection
        finally:
            connection.close()
