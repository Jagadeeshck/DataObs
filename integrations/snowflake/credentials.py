from __future__ import annotations

import os
import re
from collections.abc import Callable

from .errors import safe_error

_REF = re.compile(r"^(env|k8s|cloud|external):([^\s:][^\r\n]*)$")


def validate_reference(value: object) -> str:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise safe_error("credential_reference_invalid")
    return value


class CredentialResolver:
    """Adapter over trusted secret backends; only env is resolved locally."""

    def __init__(self, external: Callable[[str], str] | None = None) -> None:
        self.external = external

    def resolve(self, reference: str) -> str:
        reference = validate_reference(reference)
        scheme, name = reference.split(":", 1)
        value = os.environ.get(name) if scheme == "env" else (self.external(reference) if self.external else None)
        if not value:
            raise safe_error("credential_unavailable")
        return value
