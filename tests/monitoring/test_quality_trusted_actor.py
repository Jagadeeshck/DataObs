from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.api.monitor_routes import trusted_actor


def request(subject: str):
    return SimpleNamespace(state=SimpleNamespace(principal=SimpleNamespace(subject=subject)))


def test_authenticated_principal_is_authoritative_actor():
    assert trusted_actor(request("principal-123")) == "principal-123"
    assert trusted_actor(request("principal-123"), "principal-123") == "principal-123"


def test_actor_spoofing_fails_closed():
    with pytest.raises(HTTPException) as error:
        trusted_actor(request("principal-123"), "browser-supplied-actor")
    assert error.value.status_code == 403
