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
        self._negative: dict[str, float] = {}
        self._last_refresh = 0.0

    def _safe_url(self, url: str) -> str:
        parsed, issuer = urlsplit(url), urlsplit(self.issuer)

        def port(value):
            return value.port or (443 if value.scheme == "https" else 80)

        if (
            parsed.scheme != issuer.scheme
            or parsed.hostname != issuer.hostname
            or port(parsed) != port(issuer)
            or parsed.username
            or parsed.password
        ):
            raise SecurityError("oidc_endpoint_untrusted", "OIDC endpoint is outside the configured issuer")
        return url

    def _json(self, url: str) -> dict:
        try:
            with urlopen(
                Request(self._safe_url(url), headers={"Accept": "application/json"}), timeout=self.timeout
            ) as r:
                if int(r.headers.get("Content-Length", "0") or 0) > 1_000_000:
                    raise ValueError("response too large")
                final = self._safe_url(r.geturl())
                if final != r.geturl():
                    raise ValueError("untrusted redirect")
                raw = r.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ValueError("response too large")
                return json.loads(raw)
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
            if not isinstance(keys, list) or len(keys) > 100:
                raise SecurityError("jwks_unavailable", "OIDC JWKS document is malformed")
            accepted: dict[str, dict] = {}
            for key in keys:
                if not isinstance(key, dict) or not isinstance(key.get("kid"), str):
                    continue
                kid = key["kid"]
                if kid in accepted:
                    raise SecurityError("jwks_duplicate_kid", "OIDC JWKS contains duplicate key identifiers")
                if key.get("use", "sig") != "sig" or "verify" not in key.get("key_ops", ["verify"]):
                    continue
                if key.get("kty") not in {"RSA", "EC", "OKP"} or key.get("alg") not in {
                    None,
                    "RS256",
                    "RS384",
                    "RS512",
                    "PS256",
                    "PS384",
                    "PS512",
                    "ES256",
                    "ES384",
                    "ES512",
                    "EdDSA",
                }:
                    continue
                accepted[kid] = key
            self._keys = accepted
            self._expires = time.monotonic() + min(3600, max(30, self.ttl))
            self._last_refresh = time.monotonic()

    def get(self, kid: str) -> dict:
        now = time.monotonic()
        if self._negative.get(kid, 0) > now:
            raise SecurityError("signing_key_unknown", "Token signing key is unknown")
        if time.monotonic() >= self._expires:
            self.refresh()
        key = self._keys.get(kid)
        if key is None:  # exactly one controlled refresh for rotation/unknown kid
            self.refresh()
            key = self._keys.get(kid)
        if key is None:
            self._negative[kid] = time.monotonic() + 30
            raise SecurityError("signing_key_unknown", "Token signing key is unknown")
        return key
