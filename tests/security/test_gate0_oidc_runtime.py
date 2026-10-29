"""Gate 0 resource-server proof using signed JWTs and a real local HTTPS JWKS server."""

import ipaddress
import json
import ssl
import threading
import time
import urllib.request
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import AuthSettings, OIDCSettings, load_settings
from src.security.errors import SecurityError
from src.security.oidc import OIDCValidator


@pytest.fixture()
def provider(tmp_path, monkeypatch):
    signing = {name: rsa.generate_private_key(public_exponent=65537, key_size=2048) for name in ("first", "second")}
    tls_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Gate 0 synthetic issuer")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(tls_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(tls_key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "ca.pem", tmp_path / "server.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        tls_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    state = {"kid": "first", "broken": False, "requests": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            state["requests"] += 1
            key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(signing[state["kid"]].public_key()))
            key.update(kid=state["kid"], use="sig", alg="RS256")
            body = json.dumps({"keys": [] if state["broken"] else [key]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SSL_CERT_FILE", str(cert_path))
    # urllib caches an HTTPS opener and its trust context between fixtures.
    monkeypatch.setattr(urllib.request, "_opener", None)
    issuer = f"https://127.0.0.1:{server.server_port}"
    settings = OIDCSettings(
        issuer=issuer,
        audience="dataobs-api",
        jwks_url=issuer + "/jwks",
        clock_skew_seconds=0,
        allowed_token_types=("at+jwt",),
        group_role_mappings={
            r: (r,) for r in ("viewer", "tenant_admin", "operator", "collector", "workflow_approver", "platform_admin")
        },
    )

    def issue(tenant="tenant-a", role="tenant_admin", kid="first", changes=None, private_key=None):
        claims = {
            "iss": issuer,
            "aud": "dataobs-api",
            "sub": f"synthetic-{tenant}-{role}",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "groups": [role],
            "dataobs_access": [{"tenant_id": tenant, "environments": ["test"]}],
        }
        claims.update(changes or {})
        return jwt.encode(claims, private_key or signing[kid], algorithm="RS256", headers={"kid": kid, "typ": "at+jwt"})

    yield settings, state, issue
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_signature_issuer_audience_expiry_and_jwks_rotation(provider):
    settings, state, issue = provider
    validator = OIDCValidator(settings)
    assert validator.validate(issue())["sub"].startswith("synthetic-")
    assert state["requests"] > 0
    for changes, reason in [
        ({"iss": "https://invalid.example"}, "issuer_mismatch"),
        ({"aud": "other"}, "audience_mismatch"),
        ({"exp": int(time.time()) - 1}, "token_expired"),
    ]:
        with pytest.raises(SecurityError) as error:
            validator.validate(issue(changes=changes))
        assert error.value.reason_code == reason
    with pytest.raises(SecurityError) as error:
        validator.validate(issue(private_key=rsa.generate_private_key(public_exponent=65537, key_size=2048)))
    assert error.value.reason_code == "signature_invalid"
    with pytest.raises(SecurityError) as error:
        validator.validate(issue(kid="second"))
    assert error.value.reason_code == "signing_key_unknown"
    # A fresh validator has no negative-key cache from the preceding adversarial request.
    rotated = OIDCValidator(settings)
    assert rotated.validate(issue())["iss"] == settings.issuer
    state["kid"] = "second"
    assert rotated.validate(issue(kid="second"))["iss"] == settings.issuer
    state["broken"] = True
    with pytest.raises(SecurityError, match="malformed"):
        OIDCValidator(settings).validate(issue(kid="second"))


def test_jwks_tls_fails_closed_for_untrusted_ca_and_wrong_hostname(provider, monkeypatch, tmp_path):
    settings, _, issue = provider
    wrong_host = settings.issuer.replace("127.0.0.1", "localhost")
    with pytest.raises(SecurityError, match="unavailable"):
        OIDCValidator(replace(settings, issuer=wrong_host, jwks_url=wrong_host + "/jwks")).validate(issue())
    monkeypatch.delenv("SSL_CERT_FILE")
    monkeypatch.setattr(urllib.request, "_opener", None)
    with pytest.raises(SecurityError, match="unavailable"):
        OIDCValidator(settings).validate(issue())
    invalid_ca = tmp_path / "invalid-ca.pem"
    invalid_ca.write_text("invalid configured CA")
    monkeypatch.setenv("SSL_CERT_FILE", str(invalid_ca))
    monkeypatch.setattr(urllib.request, "_opener", None)
    with pytest.raises(SecurityError, match="unavailable"):
        OIDCValidator(settings).validate(issue())


def test_signed_tenant_abc_isolation_and_bounded_roles(provider):
    settings, _, issue = provider
    app_settings = replace(load_settings(), auth=AuthSettings(provider="oidc", oidc=settings), store_backend="memory")
    app = create_app(settings=app_settings)
    app.state.authenticator.authenticate(issue())
    with TestClient(app) as client:
        for tenant in ("tenant-a", "tenant-b", "tenant-c"):
            headers = {"Authorization": "Bearer " + issue(tenant)}
            response = client.post(
                "/rules",
                json={"rule_id": tenant, "dataset": tenant, "check_type": "freshness", "severity": "medium"},
                headers=headers,
            )
            assert response.status_code == 201, response.text
            own = client.get("/rules", headers=headers)
            assert own.status_code == 200 and tenant in own.text
            for other in {"tenant-a", "tenant-b", "tenant-c"} - {tenant}:
                cross = headers | {"X-DataObs-Tenant": other}
                # Read/search/mutate/delete and IAM/integration/support/lifecycle boundaries.
                for method, path in [
                    ("GET", "/rules"),
                    ("POST", "/rules"),
                    ("DELETE", "/rules/" + other),
                    ("GET", "/api/v1/assets"),
                    ("GET", "/api/v1/iam/role-bindings"),
                    ("POST", "/api/v1/iam/role-bindings"),
                    ("GET", "/api/v1/sources"),
                    ("GET", "/api/v1/platform/tenants/" + other),
                    ("POST", "/api/v1/platform/tenants/" + other + "/suspend"),
                ]:
                    denied = client.request(method, path, headers=cross, json={} if method == "POST" else None)
                    assert denied.status_code == 403, (method, path, denied.text)
                    assert "tenant_access_denied" in denied.text
        viewer = {"Authorization": "Bearer " + issue(role="viewer")}
        assert client.get("/rules", headers=viewer).status_code == 200
        assert client.post("/rules", headers=viewer, json={}).status_code == 403
        for role in ("operator", "collector", "workflow_approver"):
            headers = {"Authorization": "Bearer " + issue(role=role)}
            assert client.post("/api/v1/iam/role-bindings", headers=headers, json={}).status_code == 403


def test_legacy_quality_results_reject_cross_tenant_and_environment_access(provider):
    settings, _, issue = provider
    app_settings = replace(load_settings(), auth=AuthSettings(provider="oidc", oidc=settings), store_backend="memory")
    app = create_app(settings=app_settings)
    app.state.authenticator.authenticate(issue())
    with TestClient(app) as client:
        tenant_b = {"Authorization": "Bearer " + issue("tenant-b")}
        tenant_a = {"Authorization": "Bearer " + issue("tenant-a")}
        created = client.post(
            "/quality/results",
            json={"id": "quality-private-b", "check_name": "freshness", "table": "orders", "status": "fail", "score": 0.0},
            headers=tenant_b,
        )
        assert created.status_code == 201, created.text

        assert client.get("/quality/results/quality-private-b", headers=tenant_b).status_code == 200
        assert client.get("/quality/results/quality-private-b", headers=tenant_a).status_code == 404
        tenant_a_list = client.get("/quality/results", headers=tenant_a)
        assert tenant_a_list.status_code == 200
        assert "quality-private-b" not in tenant_a_list.text

        wrong_environment = tenant_b | {"X-DataObs-Environment": "development"}
        assert client.get("/quality/results/quality-private-b", headers=wrong_environment).status_code in {403, 404}


@pytest.mark.parametrize("operation", ["list", "search", "delete"])
def test_legacy_rules_reject_implicit_cross_tenant_access(provider, operation):
    settings, _, issue = provider
    app_settings = replace(load_settings(), auth=AuthSettings(provider="oidc", oidc=settings), store_backend="memory")
    app = create_app(settings=app_settings)
    app.state.authenticator.authenticate(issue())
    with TestClient(app) as client:
        b = {"Authorization": "Bearer " + issue("tenant-b")}
        a = {"Authorization": "Bearer " + issue("tenant-a")}
        created = client.post(
            "/rules",
            json={"rule_id": "private-b", "dataset": "private-b", "check_type": "freshness", "severity": "medium"},
            headers=b,
        )
        assert created.status_code == 201
        if operation == "delete":
            response = client.delete("/rules/private-b", headers=a)
            assert response.status_code in {403, 404}, response.text
            assert "private-b" in client.get("/rules", headers=b).text
        else:
            response = client.get("/rules", params={"dataset": "private-b"} if operation == "search" else {}, headers=a)
            assert response.status_code == 200
            assert "private-b" not in response.text, "tenant A received tenant B rule data without a tenant selector"
