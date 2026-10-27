from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable, Mapping

from .errors import error

SCOPES = ("https://www.googleapis.com/auth/pubsub", "https://www.googleapis.com/auth/monitoring.read")
REF = re.compile(r"^env:[A-Z][A-Z0-9_]{1,126}$")
PRINCIPAL = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$")


@dataclass(frozen=True)
class Authentication:
    type: str
    credential_config_ref: str | None = None
    credentials_ref: str | None = None
    target_principal: str | None = None
    delegates: tuple[str, ...] = ()
    lifetime_seconds: int = 1800


def _reference(value: object) -> str:
    if not isinstance(value, str) or not REF.fullmatch(value):
        raise error("credential_reference_invalid", "authentication")
    return value


def parse_authentication(raw: object, *, allow_legacy: bool = False) -> Authentication:
    allowed = {"type", "credential_config_ref", "credentials_ref", "target_principal", "delegates", "lifetime_seconds"}
    if not isinstance(raw, Mapping) or set(raw) - allowed:
        raise error("invalid_configuration", "authentication")
    kind = raw.get("type")
    if kind == "application_default" and len(raw) == 1:
        return Authentication(kind)
    if kind == "workload_identity" and set(raw) == {"type", "credential_config_ref"}:
        return Authentication(kind, credential_config_ref=_reference(raw.get("credential_config_ref")))
    if kind == "service_account_impersonation":
        principal, delegates, lifetime = (
            raw.get("target_principal"),
            raw.get("delegates", ()),
            raw.get("lifetime_seconds", 1800),
        )
        if (
            not isinstance(principal, str)
            or not PRINCIPAL.fullmatch(principal)
            or not isinstance(delegates, (list, tuple))
            or len(delegates) > 5
            or any(not PRINCIPAL.fullmatch(str(item)) for item in delegates)
            or isinstance(lifetime, bool)
            or not isinstance(lifetime, int)
            or not 600 <= lifetime <= 3600
        ):
            raise error("invalid_configuration", "authentication")
        return Authentication(kind, target_principal=principal, delegates=tuple(delegates), lifetime_seconds=lifetime)
    if kind == "service_account_key_legacy" and allow_legacy and set(raw) == {"type", "credentials_ref"}:
        return Authentication(kind, credentials_ref=_reference(raw.get("credentials_ref")))
    raise error("invalid_configuration", "authentication")


def _resolve(ref: str) -> str:
    value = os.environ.get(_reference(ref)[4:])
    if not value:
        raise error("credential_unavailable", "authentication")
    return value


def create_credentials(auth: Authentication, loader: Callable[[str], str] = _resolve):
    try:
        import google.auth
        from google.auth import impersonated_credentials
        from google.oauth2 import service_account
    except ImportError as exc:
        raise error("dependency_unavailable", "authentication") from exc
    if auth.type == "application_default":
        credentials, _ = google.auth.default(scopes=SCOPES)
    elif auth.type == "workload_identity":
        try:
            config = json.loads(loader(auth.credential_config_ref or ""))
        except (json.JSONDecodeError, TypeError) as exc:
            raise error("credential_format_invalid", "authentication") from exc
        if (
            config.get("type") != "external_account"
            or not str(config.get("audience", "")).startswith("//iam.googleapis.com/")
            or "executable" in config.get("credential_source", {})
        ):
            raise error("credential_format_invalid", "authentication")
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
        except (json.JSONDecodeError, TypeError) as exc:
            raise error("credential_format_invalid", "authentication") from exc
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return credentials.with_scopes(SCOPES) if getattr(credentials, "requires_scopes", False) else credentials
