from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import error


@dataclass(frozen=True, repr=False)
class BasicAuthentication:
    username: str
    password_ref: str

    def authorization_header(self) -> str:
        password = resolve_secret(self.password_ref)
        token = base64.b64encode(f"{self.username}:{password}".encode()).decode("ascii")
        return f"Basic {token}"


def parse_authentication(raw: Mapping[str, object] | None) -> BasicAuthentication:
    if not isinstance(raw, Mapping) or set(raw) != {"type", "username", "password_ref"}:
        raise error("invalid_configuration", "authentication")
    username, ref = raw.get("username"), raw.get("password_ref")
    if raw.get("type") != "basic" or not isinstance(username, str) or not username.strip():
        raise error("invalid_configuration", "authentication")
    if not isinstance(ref, str) or not (ref.startswith("env:") or ref.startswith("file-ref:")):
        raise error("credential_reference_invalid", "authentication")
    return BasicAuthentication(username.strip(), ref)


def resolve_secret(ref: str) -> str:
    if ref.startswith("env:"):
        value = os.environ.get(ref[4:])
    elif ref.startswith("file-ref:"):
        try:
            value = Path(ref[9:]).read_text(encoding="utf-8").rstrip("\r\n")
        except OSError:
            value = None
    else:
        raise error("credential_reference_invalid", "authentication")
    if not value:
        raise error("credential_unavailable", "authentication")
    return value
