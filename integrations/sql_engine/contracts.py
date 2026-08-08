from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class EngineIdentity:
    engine_type: str
    server_version: str
    provider_version: str
    client_version: str
    reachable: bool
    observed_at: datetime


@dataclass(frozen=True)
class PartialCollectionFailure:
    code: str
    capability: str
    evidence_family: str
    retryable: bool
    message: str
    catalog: str | None = None


class ConnectionFactory(Protocol):
    def connect(self, configuration: Any, *, catalog: str | None = None): ...


class SqlEngineDialect(Protocol):
    engine_type: str

    def metadata_statement(self, family: str, *, catalog: str | None = None): ...
