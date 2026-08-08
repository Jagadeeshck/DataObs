from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable, Mapping

from .errors import safe_error

REF = re.compile(r"^env:[A-Z][A-Z0-9_]{1,126}$")
PRINCIPAL = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$")
SCOPES = ("https://www.googleapis.com/auth/bigquery",)


@dataclass(frozen=True)
class Authentication:
    type: str
    credential_config_ref: str | None = None
    credentials_ref: str | None = None
    target_principal: str | None = None
    delegates: tuple[str, ...] = ()
    lifetime_seconds: int = 1800


def reference(value: object) -> str:
    if not isinstance(value, str) or not REF.fullmatch(value):
        raise safe_error("credential_reference_invalid")
    return value


def resolve(ref: str) -> str:
    value = os.environ.get(reference(ref)[4:])
    if not value:
        raise safe_error("credential_unavailable")
    return value


def parse_authentication(raw: object, *, allow_legacy: bool = False) -> Authentication:
    if not isinstance(raw, Mapping) or set(raw) - {
        "type",
        "credential_config_ref",
        "credentials_ref",
        "target_principal",
        "delegates",
        "lifetime_seconds",
    }:
        raise safe_error("invalid_configuration")
    kind = raw.get("type")
    if kind == "application_default":
        if len(raw) != 1:
            raise safe_error("invalid_configuration")
        return Authentication(kind)
    if kind == "workload_identity":
        return Authentication(kind, credential_config_ref=reference(raw.get("credential_config_ref")))
    if kind == "service_account_impersonation":
        target = raw.get("target_principal")
        delegates = raw.get("delegates", ())
        lifetime = raw.get("lifetime_seconds", 1800)
        if (
            not isinstance(target, str)
            or not PRINCIPAL.fullmatch(target)
            or not isinstance(delegates, (list, tuple))
            or len(delegates) > 5
            or any(not PRINCIPAL.fullmatch(str(x)) for x in delegates)
            or isinstance(lifetime, bool)
            or not isinstance(lifetime, int)
            or not 600 <= lifetime <= 3600
        ):
            raise safe_error("invalid_configuration")
        return Authentication(kind, target_principal=target, delegates=tuple(delegates), lifetime_seconds=lifetime)
    if kind == "service_account_key_legacy" and allow_legacy:
        return Authentication(kind, credentials_ref=reference(raw.get("credentials_ref")))
    raise safe_error("invalid_configuration")


def create_credentials(auth: Authentication, loader: Callable[[str], str] = resolve):
    try:
        import google.auth
        from google.auth import impersonated_credentials
        from google.oauth2 import service_account
    except ImportError as exc:
        raise safe_error("dependency_unavailable") from exc
    if auth.type == "application_default":
        credentials, _ = google.auth.default(scopes=SCOPES)
    elif auth.type == "workload_identity":
        material = loader(auth.credential_config_ref or "")
        try:
            config = json.loads(material)
        except json.JSONDecodeError as exc:
            raise safe_error("credential_format_invalid") from exc
        if (
            config.get("type") != "external_account"
            or not str(config.get("audience", "")).startswith("//iam.googleapis.com/")
            or "executable" in config.get("credential_source", {})
        ):
            raise safe_error("credential_format_invalid")
        credentials, _ = google.auth.load_credentials_from_dict(config, scopes=SCOPES)
    elif auth.type == "service_account_impersonation":
        source, _ = google.auth.default(scopes=SCOPES)
        credentials = impersonated_credentials.Credentials(
            source_credentials=source,
            target_principal=auth.target_principal,
            target_scopes=SCOPES,
            delegates=list(auth.delegates),
            lifetime=auth.lifetime_seconds,
        )
    else:
        try:
            info = json.loads(loader(auth.credentials_ref or ""))
        except json.JSONDecodeError as exc:
            raise safe_error("credential_format_invalid") from exc
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    if getattr(credentials, "requires_scopes", False):
        credentials = credentials.with_scopes(SCOPES)
    return credentials
