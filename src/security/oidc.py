from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import jwt

from src.config.settings import OIDCSettings

from .errors import SecurityError
from .jwks import JWKSClient


class OIDCValidator:
    def __init__(self, settings: OIDCSettings):
        self.settings = settings
        self.jwks = JWKSClient(
            settings.issuer,
            settings.jwks_url,
            settings.discovery_timeout_seconds,
            settings.jwks_cache_ttl_seconds,
            settings.jwks_last_known_good_seconds,
        )

    def validate(self, token: str) -> dict[str, Any]:
        if not token or len(token) > self.settings.maximum_token_bytes:
            raise SecurityError("token_malformed", "Access token is malformed")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise SecurityError("token_malformed", "Access token is malformed") from exc
        alg, kid = header.get("alg"), header.get("kid")
        if alg == "none" or alg not in self.settings.allowed_algorithms:
            raise SecurityError("algorithm_unsupported", "Token signing algorithm is not allowed")
        if not isinstance(kid, str) or not kid:
            raise SecurityError("signing_key_unknown", "Token signing key identifier is missing")
        try:
            claims = jwt.decode(
                token,
                jwt.PyJWK.from_dict(self.jwks.get(kid)).key,
                algorithms=list(self.settings.allowed_algorithms),
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                leeway=self.settings.clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "aud", self.settings.subject_claim]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise SecurityError("token_expired", "Access token has expired") from exc
        except jwt.ImmatureSignatureError as exc:
            raise SecurityError("token_not_yet_valid", "Access token is not yet valid") from exc
        except jwt.InvalidIssuerError as exc:
            raise SecurityError("issuer_mismatch", "Access token issuer is invalid") from exc
        except jwt.InvalidAudienceError as exc:
            raise SecurityError("audience_mismatch", "Access token audience is invalid") from exc
        except jwt.MissingRequiredClaimError as exc:
            raise SecurityError("mandatory_claim_missing", "Access token is missing a mandatory claim") from exc
        except jwt.PyJWTError as exc:
            raise SecurityError("signature_invalid", "Access token validation failed") from exc
        if int(claims["iat"]) > int(datetime.now(timezone.utc).timestamp()) + self.settings.clock_skew_seconds:
            raise SecurityError("token_not_yet_valid", "Access token issue time is in the future")
        scopes = set(str(claims.get("scope", "")).split())
        if not set(self.settings.required_scopes).issubset(scopes):
            raise SecurityError("required_scope_missing", "Access token lacks a required scope")
        return claims
