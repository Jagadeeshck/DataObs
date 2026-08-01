from __future__ import annotations

import json
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .errors import SecurityError


class JWKSClient:
    MAX_RESPONSE_BYTES = 1_000_000
    MAX_KEYS = 100

    def __init__(self, issuer: str, jwks_url: str | None, timeout: float, ttl: int, last_known_good: int = 60):
        self.issuer = issuer.rstrip("/")
        self.jwks_url = jwks_url
        self.timeout = timeout
        self.ttl = ttl
        self.last_known_good = last_known_good
        self._keys: dict[str, dict] = {}
        self._expires = 0.0
        self._stale_until = 0.0
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
                if int(r.headers.get("Content-Length", "0") or 0) > self.MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
                final = self._safe_url(r.geturl())
                if final != r.geturl():
                    raise ValueError("untrusted redirect")
                payload = r.read(self.MAX_RESPONSE_BYTES + 1)
                if len(payload) > self.MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
                document = json.loads(payload)
                if not isinstance(document, dict):
                    raise ValueError("response is not an object")
                return document
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
            if not isinstance(keys, list) or not keys or len(keys) > self.MAX_KEYS:
                raise SecurityError("jwks_unavailable", "OIDC JWKS document is malformed")
            accepted: dict[str, dict] = {}
            for key in keys:
                if not isinstance(key, dict) or not isinstance(key.get("kid"), str) or not key["kid"]:
                    raise SecurityError("jwks_unavailable", "OIDC JWKS document is malformed")
                if key["kid"] in accepted:
                    raise SecurityError("jwks_duplicate_kid", "OIDC JWKS contains duplicate key identifiers")
                if key.get("use") not in {None, "sig"}:
                    continue
                if key.get("kty") not in {"RSA", "EC", "OKP"}:
                    continue
                accepted[key["kid"]] = key
            if not accepted:
                raise SecurityError("jwks_unavailable", "OIDC JWKS contains no signing keys")
            now = time.monotonic()
            self._keys = accepted
            self._expires = now + max(1, self.ttl)
            self._stale_until = self._expires + max(0, self.last_known_good)
            self._last_refresh = now

    def get(self, kid: str) -> dict:
        now = time.monotonic()
        if self._negative.get(kid, 0) > now:
            raise SecurityError("signing_key_unknown", "Token signing key is unknown")
        if now >= self._expires:
            try:
                self.refresh()
            except SecurityError:
                # A known key may bridge a bounded provider outage. Unknown keys
                # never use this path and every request retries after expiry.
                if kid not in self._keys or now > self._stale_until:
                    raise
        key = self._keys.get(kid)
        if key is None:  # exactly one controlled refresh for rotation/unknown kid
            self.refresh()
            key = self._keys.get(kid)
        if key is None:
            self._negative[kid] = time.monotonic() + 30
            raise SecurityError("signing_key_unknown", "Token signing key is unknown")
        return key
