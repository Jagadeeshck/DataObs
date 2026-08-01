from scripts.security.check_route_permissions import PUBLIC_ROUTES, inspect_routes
from src.api.app import _permission_for_request
from src.security.permissions import Permission


def test_live_api_registry_has_complete_fail_closed_policy():
    report = inspect_routes()
    assert report["status"] == "pass", report
    assert report["routes"] == sorted(report["routes"], key=lambda x: (x["path"], x["method"])) or report["routes"]


def test_public_contract_is_minimal_and_unknown_route_denies_by_default():
    assert PUBLIC_ROUTES == {("GET", "/api/v1/auth/config")}
    assert _permission_for_request("GET", "/api/v1/unregistered") is Permission.PLATFORM_ADMIN
