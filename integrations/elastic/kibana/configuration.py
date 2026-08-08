from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

_SPACE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class KibanaConfiguration:
    base_url: str
    api_key: str | None = field(default=None, repr=False)
    spaces: dict[str, str] = field(default_factory=dict)
    production: bool = True
    connect_timeout: float = 3.0
    read_timeout: float = 15.0
    max_response_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in ({"https"} if self.production else {"http", "https"}):
            raise ValueError("Kibana base URL must use HTTPS")
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("invalid Kibana base URL")
        if parsed.path not in {"", "/"}:
            raise ValueError("Kibana base URL must not contain a path")
        if not 1 <= self.max_response_bytes <= 8 * 1024 * 1024:
            raise ValueError("invalid Kibana response limit")
        for environment, space in self.spaces.items():
            if not environment or (space != "default" and not _SPACE.fullmatch(space)):
                raise ValueError("invalid Kibana space mapping")

    @classmethod
    def from_env(cls, *, credential_variable: str = "KIBANA_API_KEY") -> "KibanaConfiguration":
        mappings: dict[str, str] = {}
        for entry in os.getenv("DATAOBS_KIBANA_SPACES", "").split(","):
            if entry.strip():
                environment, separator, space = entry.partition("=")
                if not separator:
                    raise ValueError("invalid DATAOBS_KIBANA_SPACES")
                mappings[environment.strip()] = space.strip()
        return cls(
            base_url=os.environ["KIBANA_URL"],
            api_key=os.getenv(credential_variable),
            spaces=mappings,
            production=os.getenv("DATAOBS_ENV", "production").lower() not in {"dev", "development", "test"},
        )

    def space_for(self, environment: str) -> str:
        try:
            return self.spaces[environment]
        except KeyError as exc:
            raise ValueError("Kibana space is not configured for environment") from exc
