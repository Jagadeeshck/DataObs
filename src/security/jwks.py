from __future__ import annotations

import json
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .errors import SecurityError


class JWKSClient:
    def __init__(self, issuer: str, jwks_url: str | None, timeout: float, ttl: int):
        self.issuer = issuer.rstrip("/")
        self.jwks_url = jwks_url
        self.timeout = timeout
        self.ttl = ttl
        self._keys: dict[str, dict] = {}
        self._expires = 0.0
        self._lock = threading.Lock()

    def _safe_url(self, url: str) -> str:
        parsed, issuer = urlsplit(url), urlsplit(self.issuer)
        if parsed.scheme != issuer.scheme or parsed.hostname != issuer.hostname or parsed.username or parsed.password:
            raise SecurityError("oidc_endpoint_untrusted", "OIDC endpoint is outside the configured issuer")
        return url

    def _json(self, url: str) -> dict:
        try:
            with urlopen(
                Request(self._safe_url(url), headers={"Accept": "application/json"}), timeout=self.timeout
            ) as r:
                if int(r.headers.get("Content-Length", "0") or 0) > 1_000_000:
                    raise ValueError("response too large")
                return json.loads(r.read(1_000_001))
        except SecurityError:
            raise
        except Exception as exc:
            raise SecurityError("jwks_unavailable", "OIDC signing keys are unavailable") from exc

    def refresh(self) -> None:
        with self._lock:
            url = self.jwks_url
            if not url:
                discovery = self._json(f"{self.issuer}/.well-known/openid-configuration")
                if discovery.get("issuer", "").rstrip("/") != self.issuer:
                    raise SecurityError("issuer_mismatch", "OIDC discovery issuer mismatch")
                url = discovery.get("jwks_uri")
            if not isinstance(url, str):
                raise SecurityError("jwks_unavailable", "OIDC JWKS URL is missing")
            document = self._json(url)
            keys = document.get("keys")
            if not isinstance(keys, list):
                raise SecurityError("jwks_unavailable", "OIDC JWKS document is malformed")
            self._keys = {str(k["kid"]): k for k in keys if isinstance(k, dict) and k.get("kid")}
            self._expires = time.monotonic() + self.ttl

    def get(self, kid: str) -> dict:
        if time.monotonic() >= self._expires:
            self.refresh()
        key = self._keys.get(kid)
        if key is None:  # exactly one controlled refresh for rotation/unknown kid
            self.refresh()
            key = self._keys.get(kid)
        if key is None:
            raise SecurityError("signing_key_unknown", "Token signing key is unknown")
        return key
