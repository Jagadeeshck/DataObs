from __future__ import annotations

import os

from .errors import SqlServerCollectorError


def resolve_secret(reference: str) -> str:
    if reference.startswith(("env:", "env://")):
        value = os.environ.get(reference.split(":", 1)[1].lstrip("/"))
    elif reference.startswith(("file-ref:", "file://", "k8s-file://")):
        with open(reference.split(":", 1)[1].lstrip("/"), encoding="utf-8") as handle:
            value = handle.read().strip()
    else:
        value = None
    if not value:
        raise SqlServerCollectorError("credential_unavailable")
    return value


def authentication_options(configuration) -> dict[str, str]:
    auth = configuration.authentication
    if auth["type"] == "sql_password":
        return {"UID": auth["username"], "PWD": resolve_secret(auth["password_ref"])}
    if auth["type"] == "entra_managed_identity":
        return {"Authentication": "ActiveDirectoryMSI"}
    return {
        "Authentication": "ActiveDirectoryServicePrincipal",
        "UID": auth["client_id"],
        "PWD": resolve_secret(auth["client_secret_ref"]),
    }
