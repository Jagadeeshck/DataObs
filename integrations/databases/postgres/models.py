from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PostgresConnectionConfig:
    host: str
    port: int
    database: str
    username: str
    password_ref: str
    sslmode: str = "prefer"
    sslrootcert: str | None = None
    connect_timeout: int = 5
    statement_timeout_ms: int = 5000
    application_name: str = "dataobs_scanner"
    keepalives: int = 1

    def __repr__(self):
        return f"PostgresConnectionConfig(host={self.host!r}, port={self.port}, database={self.database!r}, username={self.username!r}, password_ref=SecretRef(**redacted**))"
