from contextlib import contextmanager

from .authentication import resolve_secret
from .errors import OracleCollectorError


class OracleConnectionFactory:
    @contextmanager
    def connect(self, cfg):
        try:
            import oracledb
        except ImportError as exc:
            raise OracleCollectorError("dependency_unavailable") from exc
        # Structured Thin-mode parameters: no user supplied descriptor or privileged mode.
        params = oracledb.ConnectParams(
            host=cfg.host,
            port=cfg.port,
            service_name=cfg.service_name,
            protocol="tcps",
            ssl_server_dn_match=True,
            ssl_server_cert_dn=cfg.tls.get("server_certificate_dn"),
            tcp_connect_timeout=cfg.limits["connection_timeout_seconds"],
        )
        connection = oracledb.connect(
            user=cfg.authentication["username"],
            password=resolve_secret(cfg.authentication["password_ref"]),
            params=params,
        )
        connection.call_timeout = cfg.limits["statement_timeout_seconds"] * 1000
        try:
            yield connection
        finally:
            connection.close()
