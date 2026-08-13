import os

from .errors import OracleCollectorError


def resolve_secret(reference: str) -> str:
    if reference.startswith(("env:", "env://")):
        value = os.environ.get(reference.split(":", 1)[1].lstrip("/"))
    elif reference.startswith(("file-ref:", "file://", "k8s-file://")):
        with open(reference.split(":", 1)[1].lstrip("/"), encoding="utf-8") as handle:
            value = handle.read().strip()
    else:
        value = None
    if not value:
        raise OracleCollectorError("credential_unavailable")
    return value
