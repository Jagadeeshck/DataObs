from __future__ import annotations

import os
from contextlib import contextmanager

from .errors import MySqlCollectorError


def resolve_secret(reference: str) -> str:
    if reference.startswith(("env:", "env://")):
        value = os.environ.get(reference.split(":", 1)[1].lstrip("/"))
    elif reference.startswith(("file-ref:", "file://", "k8s-file://")):
        with open(reference.split(":", 1)[1].lstrip("/"), encoding="utf-8") as handle:
            value = handle.read().strip()
    else:
        value = None
    if not value:
        raise MySqlCollectorError("credential_unavailable")
    return value


class MySqlConnectionFactory:
    @contextmanager
    def connect(self, cfg):
        try:
            import mysql.connector
        except ImportError as exc:
            raise MySqlCollectorError("dependency_unavailable") from exc
        connection = mysql.connector.connect(
            host=cfg.host,
            port=cfg.port,
            database=cfg.database,
            user=cfg.username,
            password=resolve_secret(cfg.password_ref),
            connection_timeout=cfg.limits["connection_timeout_seconds"],
            read_timeout=cfg.limits["read_timeout_seconds"],
            write_timeout=cfg.limits["write_timeout_seconds"],
            ssl_disabled=False,
            ssl_verify_cert=True,
            ssl_verify_identity=True,
            ssl_ca=cfg.ca_bundle_ref.split(":", 1)[1].lstrip("/"),
            allow_local_infile=False,
            autocommit=True,
            conn_attrs={"_client_name": "dataobs-collector"},
        )
        try:
            yield connection
        finally:
            connection.close()
