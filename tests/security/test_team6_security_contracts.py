from __future__ import annotations

import json
import time

import jwt
import pytest

from scripts.security.check_route_permissions import build_report
from src.config.settings import OIDCSettings
from src.security.audit import security_event
from src.security.errors import SecurityError
from src.security.oidc import OIDCValidator
from src.security.route_policy import PUBLIC_ROUTES, permission_for_route

SIGNING_SECRET = "x" * 64
SIGNING_SECRET_JWK = "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eA"


def test_live_v1_route_registry_has_complete_explicit_policy():
    report = build_report()
    assert report["status"] == "pass", report["errors"]
    assert report["route_count"] > 50


def test_unknown_routes_fail_closed_and_public_route_is_explicit():
    assert ("GET", "/api/v1/auth/config") in PUBLIC_ROUTES
    with pytest.raises(LookupError, match="no permission policy"):
        permission_for_route("GET", "/api/v1/new-unreviewed-capability")
    with pytest.raises(LookupError, match="public routes"):
        permission_for_route("GET", "/api/v1/auth/config")


def test_security_event_has_fixed_bounded_redaction_safe_schema():
    event = security_event(
        event_type="auth.denied",
        outcome="failure",
        reason_code="signature_invalid",
        principal_id="anonymous",
        tenant_id=None,
        environment=None,
        request_id="r" * 500,
        route_template="/api/v1/assets",
    )
    assert set(event) == {
        "schema_version",
        "event_type",
        "outcome",
        "reason_code",
        "principal_id",
        "tenant_id",
        "environment",
        "request_id",
        "route_template",
        "timestamp",
        "source_component",
    }
    assert len(event["request_id"]) == 256
    encoded = json.dumps(event).lower()
    for forbidden in ("authorization", "access_token", "refresh_token", "password", "cookie", "jwt"):
        assert forbidden not in encoded


def _validator() -> OIDCValidator:
    validator = OIDCValidator(
        OIDCSettings(
            issuer="https://identity.example.test/realms/dataobs",
            audience="dataobs-api",
            allowed_algorithms=("HS256",),
        )
    )
    validator.jwks.get = lambda kid: {  # type: ignore[method-assign]
        "kty": "oct",
        "kid": kid,
        "k": SIGNING_SECRET_JWK,
    }
    return validator


def _token(**changes):
    now = int(time.time())
    claims = {
        "sub": "principal-1",
        "iss": "https://identity.example.test/realms/dataobs",
        "aud": "dataobs-api",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(changes)
    return jwt.encode(claims, SIGNING_SECRET, algorithm="HS256", headers={"kid": "key-1"})


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"exp": 1}, "token_expired"),
        ({"iss": "https://wrong.example"}, "issuer_mismatch"),
        ({"aud": "wrong-api"}, "audience_mismatch"),
    ],
)
def test_oidc_expiry_issuer_and_audience_fail_closed(changes, reason):
    with pytest.raises(SecurityError) as caught:
        _validator().validate(_token(**changes))
    assert caught.value.reason_code == reason
    assert _token(**changes) not in str(caught.value)


def test_oidc_unexpected_algorithm_malformed_and_unknown_kid_fail_closed():
    validator = _validator()
    unexpected = jwt.encode({"sub": "x"}, SIGNING_SECRET, algorithm="HS384", headers={"kid": "key-1"})
    with pytest.raises(SecurityError) as algorithm:
        validator.validate(unexpected)
    assert algorithm.value.reason_code == "algorithm_unsupported"
    with pytest.raises(SecurityError) as malformed:
        validator.validate("not-a-jwt")
    assert malformed.value.reason_code == "token_malformed"
    validator.jwks.get = lambda _: (_ for _ in ()).throw(  # type: ignore[method-assign]
        SecurityError("signing_key_unknown", "Token signing key is unknown")
    )
    with pytest.raises(SecurityError) as unknown:
        validator.validate(_token())
    assert unknown.value.reason_code == "signing_key_unknown"
