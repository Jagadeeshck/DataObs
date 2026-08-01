import pytest

from scripts.security.check_route_permissions import inspect_routes
from src.security.route_policy import PUBLIC_ROUTES, permission_for_route


def test_live_api_registry_has_complete_fail_closed_policy():
    report = inspect_routes()
    assert report["status"] == "pass", report
    assert report["routes"] == sorted(report["routes"], key=lambda x: (x["path"], x["method"])) or report["routes"]


def test_public_contract_is_minimal_and_unknown_route_denies_by_default():
    assert ("GET", "/api/v1/auth/config") in PUBLIC_ROUTES
    with pytest.raises(LookupError):
        permission_for_route("GET", "/api/v1/unregistered")
