import importlib
import importlib.metadata
import os
from contextlib import contextmanager
from urllib.parse import urlsplit

import requests

SOURCE = "dataobs-collector"


def _resolve(reference: str) -> str:
    if reference.startswith("env:"):
        value = os.environ.get(reference[4:])
        if not value:
            raise RuntimeError("credential_unavailable")
        return value
    if reference.startswith("file-ref:"):
        path = reference[9:]
        if not path.startswith("/"):
            raise RuntimeError("credential_reference_invalid")
        with open(path, encoding="utf-8") as handle:
            value = handle.read().strip()
        if not value:
            raise RuntimeError("credential_unavailable")
        return value
    raise RuntimeError("credential_reference_invalid")


def validate_next_uri(uri: str, host: str, port: int) -> None:
    parsed = urlsplit(uri)
    if (
        parsed.scheme != "https"
        or parsed.hostname != host.lower()
        or parsed.port != port
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise RuntimeError("coordinator_unavailable")


class _CoordinatorSession(requests.Session):
    """Confines every protocol request, including server-provided nextUri."""

    def __init__(self, host, port, verify):
        super().__init__()
        self._host, self._port, self.verify = host, port, verify

    def request(self, method, url, *args, **kwargs):
        validate_next_uri(url, self._host, self._port)
        kwargs.setdefault("allow_redirects", False)
        return super().request(method, url, *args, **kwargs)


class PrestoConnectionFactory:
    """Lazy adapter for the official PrestoDB DBAPI client."""

    @contextmanager
    def connect(self, cfg, *, catalog=None):
        try:
            dbapi = importlib.import_module("prestodb.dbapi")
            auth_module = importlib.import_module("prestodb.auth")
            importlib.metadata.version("presto-python-client")
        except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
            raise RuntimeError("dependency_unavailable") from exc
        authentication = auth_module.BasicAuthentication(
            cfg.authentication.username, _resolve(cfg.authentication.password_ref)
        )
        verify = _resolve(cfg.ca_bundle_ref) if cfg.ca_bundle_ref else True
        connection = dbapi.connect(
            host=cfg.host,
            port=cfg.port,
            http_scheme="https",
            user=cfg.authentication.username,
            auth=authentication,
            source=SOURCE,
            catalog=catalog,
        )
        connection._http_session = _CoordinatorSession(cfg.host, cfg.port, verify)
        authentication.set_http_session(connection._http_session)
        try:
            yield connection
        finally:
            connection.close()
