import os
import re
from dataclasses import dataclass
from typing import Callable, Mapping

from .errors import safe_error

REF = re.compile(r"^env:[A-Z][A-Z0-9_]{1,126}$")


@dataclass(frozen=True)
class Authentication:
    type: str
    tenant_id: str | None = None
    client_id_ref: str | None = None
    client_secret_ref: str | None = None
    token_file_ref: str | None = None


def reference(v):
    if not isinstance(v, str) or not REF.fullmatch(v):
        raise safe_error("credential_reference_invalid")
    return v


def resolve(ref):
    value = os.environ.get(reference(ref)[4:])
    if not value:
        raise safe_error("credential_unavailable")
    return value


def parse_authentication(raw, tenant_id):
    if not isinstance(raw, Mapping) or set(raw) - {
        "type",
        "tenant_id",
        "client_id_ref",
        "client_secret_ref",
        "token_file_ref",
    }:
        raise safe_error("invalid_configuration")
    kind = raw.get("type")
    if raw.get("tenant_id") not in (None, tenant_id):
        raise safe_error("tenant_mismatch")
    if kind == "managed_identity":
        return Authentication(kind, tenant_id, reference(raw["client_id_ref"]) if "client_id_ref" in raw else None)
    if kind == "workload_identity":
        return Authentication(
            kind, tenant_id, reference(raw.get("client_id_ref")), token_file_ref=reference(raw.get("token_file_ref"))
        )
    if kind == "service_principal_secret":
        return Authentication(
            kind, tenant_id, reference(raw.get("client_id_ref")), reference(raw.get("client_secret_ref"))
        )
    raise safe_error("invalid_configuration")


def create_credential(auth: Authentication, loader: Callable[[str], str] = resolve):
    try:
        from azure.identity import ClientSecretCredential, ManagedIdentityCredential, WorkloadIdentityCredential
    except ImportError as exc:
        raise safe_error("dependency_unavailable") from exc
    if auth.type == "managed_identity":
        return ManagedIdentityCredential(client_id=loader(auth.client_id_ref) if auth.client_id_ref else None)
    if auth.type == "workload_identity":
        token_path = loader(auth.token_file_ref or "")
        if not os.path.isabs(token_path):
            raise safe_error("credential_reference_invalid")
        return WorkloadIdentityCredential(
            tenant_id=auth.tenant_id, client_id=loader(auth.client_id_ref or ""), token_file_path=token_path
        )
    return ClientSecretCredential(
        tenant_id=auth.tenant_id,
        client_id=loader(auth.client_id_ref or ""),
        client_secret=loader(auth.client_secret_ref or ""),
    )
