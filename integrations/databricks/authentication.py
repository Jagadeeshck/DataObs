from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import safe_error


def validate_secret_reference(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("env:") or len(value) <= 4:
        raise safe_error("credential_reference_invalid")
    return value


def resolve_secret(reference: str) -> str:
    name = validate_secret_reference(reference)[4:]
    value = os.environ.get(name)
    if not value:
        raise safe_error("credential_unavailable")
    return value


@dataclass(frozen=True)
class Authentication:
    type: str
    client_id_ref: str | None = None
    client_secret_ref: str | None = None
    token_ref: str | None = None


def parse_authentication(raw: object, *, allow_legacy_pat: bool) -> Authentication:
    if not isinstance(raw, dict) or set(raw) - {"type", "client_id_ref", "client_secret_ref", "token_ref"}:
        raise safe_error("invalid_configuration")
    kind = raw.get("type")
    if kind == "oauth_m2m":
        return Authentication(
            kind,
            validate_secret_reference(raw.get("client_id_ref")),
            validate_secret_reference(raw.get("client_secret_ref")),
        )
    if kind == "pat_legacy" and allow_legacy_pat:
        return Authentication(kind, token_ref=validate_secret_reference(raw.get("token_ref")))
    raise safe_error("invalid_configuration")
