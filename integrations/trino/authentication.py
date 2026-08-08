import re
from dataclasses import dataclass
from typing import Mapping

_USER = re.compile(r"[A-Za-z0-9_.@-]{1,128}")


def _ref(value, *, file_allowed=False):
    prefixes = ("env:", "file-ref:") if file_allowed else ("env:",)
    if not isinstance(value, str) or not value.startswith(prefixes) or len(value) > 512:
        raise ValueError("credential_reference_invalid")
    return value


@dataclass(frozen=True)
class Authentication:
    type: str
    user: str
    secret_ref: str
    private_key_ref: str | None = None


def parse_authentication(raw: Mapping):
    if not isinstance(raw, Mapping):
        raise ValueError("invalid_configuration")
    kind = raw.get("type")
    allowed = {
        "basic": {"type", "username", "password_ref"},
        "jwt": {"type", "user", "token_ref"},
        "certificate": {"type", "user", "certificate_ref", "private_key_ref"},
    }
    if kind not in allowed or set(raw) != allowed[kind]:
        raise ValueError("invalid_configuration")
    user = raw.get("username" if kind == "basic" else "user")
    if not isinstance(user, str) or not _USER.fullmatch(user):
        raise ValueError("invalid_configuration")
    if kind == "basic":
        return Authentication(kind, user, _ref(raw["password_ref"]))
    if kind == "jwt":
        return Authentication(kind, user, _ref(raw["token_ref"]))
    return Authentication(
        kind, user, _ref(raw["certificate_ref"], file_allowed=True), _ref(raw["private_key_ref"], file_allowed=True)
    )
