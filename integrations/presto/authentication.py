import re
from dataclasses import dataclass
from typing import Mapping

_USER = re.compile(r"[A-Za-z0-9_.@-]{1,128}")


@dataclass(frozen=True)
class Authentication:
    type: str
    username: str
    password_ref: str


def parse_authentication(raw: Mapping) -> Authentication:
    if not isinstance(raw, Mapping) or set(raw) != {"type", "username", "password_ref"} or raw.get("type") != "basic":
        raise ValueError("invalid_configuration")
    username, reference = raw.get("username"), raw.get("password_ref")
    if not isinstance(username, str) or not _USER.fullmatch(username):
        raise ValueError("invalid_configuration")
    if not isinstance(reference, str) or not reference.startswith("env:") or len(reference) > 512:
        raise ValueError("credential_reference_invalid")
    return Authentication("basic", username, reference)
