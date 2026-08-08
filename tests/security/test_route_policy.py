def test_operator_can_request_approval():
    from src.security.permissions import Permission
    from src.security.route_policy import permission_for_route

    assert permission_for_route("POST", "/api/v1/incident-automation/approvals") == Permission.WORKFLOWS_EXECUTE


def test_operator_cannot_approve():
    from src.security.permissions import Permission
    from src.security.route_policy import permission_for_route

    assert (
        permission_for_route("POST", "/api/v1/incident-automation/approvals/{approval_id}/approve")
        == Permission.WORKFLOWS_APPROVE
    )
    assert Permission.WORKFLOWS_APPROVE != Permission.WORKFLOWS_EXECUTE


def test_approver_can_decide():
    from src.security.permissions import Permission
    from src.security.route_policy import permission_for_route

    assert (
        permission_for_route("POST", "/api/v1/incident-automation/approvals/{approval_id}/reject")
        == Permission.WORKFLOWS_APPROVE
    )


def test_reader_cannot_request_action():
    from src.security.permissions import Permission
    from src.security.route_policy import permission_for_route

    assert permission_for_route("POST", "/api/v1/incident-automation/executions") == Permission.WORKFLOWS_EXECUTE
    assert Permission.WORKFLOWS_EXECUTE != Permission.INCIDENTS_READ
