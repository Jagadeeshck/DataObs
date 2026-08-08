import importlib
import os
from contextlib import contextmanager


def _resolve(ref: str) -> str:
    if ref.startswith("env:"):
        value = os.environ.get(ref[4:])
        if not value:
            raise RuntimeError("credential_unavailable")
        return value
    if ref.startswith("file-ref:"):
        path = ref[9:]
        if not path.startswith("/"):
            raise RuntimeError("credential_reference_invalid")
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    raise RuntimeError("credential_reference_invalid")


class TrinoConnectionFactory:
    """Lazy official-client adapter. No import side effect for non-Trino providers."""

    @contextmanager
    def connect(self, cfg, *, catalog=None):
        try:
            dbapi = importlib.import_module("trino.dbapi")
            auth_module = importlib.import_module("trino.auth")
        except ImportError as exc:
            raise RuntimeError("dependency_unavailable") from exc
        auth = cfg.authentication
        if auth.type == "basic":
            authentication = auth_module.BasicAuthentication(auth.user, _resolve(auth.secret_ref))
        elif auth.type == "jwt":
            authentication = auth_module.JWTAuthentication(_resolve(auth.secret_ref))
        else:
            authentication = auth_module.CertificateAuthentication(
                _resolve(auth.secret_ref), _resolve(auth.private_key_ref)
            )
        verify = _resolve(cfg.ca_bundle_ref) if cfg.ca_bundle_ref else True
        connection = dbapi.connect(
            host=cfg.host,
            port=cfg.port,
            http_scheme="https",
            user=auth.user,
            auth=authentication,
            source="dataobs-collector",
            catalog=catalog,
            timezone="UTC",
            verify=verify,
        )
        try:
            yield connection
        finally:
            connection.close()
