from __future__ import annotations

import os
import time

from .models import PostgresConnectionConfig


class SecretValue(str):
    def __repr__(self):
        return "SecretValue(**redacted**)"


def resolve_secret(ref: str) -> SecretValue:
    if ref.startswith("env://"):
        return SecretValue(os.environ[ref[6:]])
    if ref.startswith("file://"):
        return SecretValue(open(ref[7:], encoding="utf-8").read().strip())
    if ref.startswith("k8s-file://"):
        return SecretValue(open(ref[11:], encoding="utf-8").read().strip())
    raise ValueError("PostgreSQL passwords must be supplied by env://, file://, or k8s-file:// secret references")


def connect(config: PostgresConnectionConfig):
    import psycopg

    password = resolve_secret(config.password_ref)
    kwargs = dict(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.username,
        password=str(password),
        connect_timeout=config.connect_timeout,
        application_name=config.application_name,
        sslmode=config.sslmode,
        options=f"-c statement_timeout={config.statement_timeout_ms}",
    )
    if config.sslrootcert:
        kwargs["sslrootcert"] = config.sslrootcert
    last: BaseException | None = None
    for _ in range(3):
        try:
            conn = psycopg.connect(**kwargs)
            conn.read_only = True
            conn.autocommit = False
            return conn
        except Exception as exc:
            last = exc
            time.sleep(0.2)
    if last is not None:
        raise last
    raise RuntimeError("PostgreSQL connection failed")


def query_tag(scanner_id: str, task_id: str, operation: str) -> str:
    return f"/* dataobs scanner={scanner_id} task={task_id} operation={operation} */"
