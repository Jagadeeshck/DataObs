from __future__ import annotations

import os
from contextlib import contextmanager

from .errors import MariaDbCollectorError


def resolve_secret(reference: str) -> str:
    if reference.startswith(("env:", "env://")):
        value = os.environ.get(reference.split(":", 1)[1].removeprefix("//"))
    elif reference.startswith(("file-ref:", "file://", "k8s-file://")):
        with open(reference.split(":", 1)[1].removeprefix("//"), encoding="utf-8") as handle:
            value = handle.read().strip()
    else:
        value = None
    if not value:
        raise MariaDbCollectorError("credential_unavailable")
    return value


class MariaDbConnectionFactory:
    @contextmanager
    def connect(self, cfg):
        try:
            import mariadb
        except ImportError as exc:
            raise MariaDbCollectorError("dependency_unavailable") from exc
        connection = mariadb.connect(
            host=cfg.host,
            port=cfg.port,
            database=cfg.database,
            user=cfg.username,
            password=resolve_secret(cfg.password_ref),
            connect_timeout=cfg.limits["connection_timeout_seconds"],
            read_timeout=cfg.limits["read_timeout_seconds"],
            write_timeout=cfg.limits["write_timeout_seconds"],
            ssl_verify_cert=True,
            ssl_ca=cfg.ca_bundle_ref.split(":", 1)[1].removeprefix("//"),
            local_infile=False,
            autocommit=True,
        )
        try:
            yield connection
        finally:
            connection.close()
