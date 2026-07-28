from .permissions import Permission

READ = frozenset(p for p in Permission if p.value.endswith(":read"))
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "platform_admin": frozenset(Permission),
    "tenant_admin": frozenset(Permission) - {Permission.PLATFORM_ADMIN},
    "operator": READ
    | frozenset(
        {
            Permission.MONITORS_WRITE,
            Permission.MONITORS_EXECUTE,
            Permission.QUALITY_EXECUTE,
            Permission.JOBS_EXECUTE,
            Permission.STREAMS_EXECUTE,
            Permission.INCIDENTS_WRITE,
            Permission.WORKFLOWS_EXECUTE,
        }
    ),
    "investigator": READ | frozenset({Permission.INCIDENTS_WRITE}),
    "monitor_editor": READ
    | frozenset(
        {
            Permission.MONITORS_WRITE,
            Permission.MONITORS_EXECUTE,
            Permission.QUALITY_WRITE,
            Permission.QUALITY_EXECUTE,
        }
    ),
    "workflow_approver": READ | frozenset({Permission.WORKFLOWS_APPROVE}),
    "viewer": READ,
    "collector": frozenset({Permission.AUTH_READ, Permission.COLLECTION_INGEST}),
}

for _role in tuple(ROLE_PERMISSIONS):
    ROLE_PERMISSIONS[_role] = ROLE_PERMISSIONS[_role] | {Permission.AUTH_READ}


def permissions_for_roles(roles: set[str] | frozenset[str]) -> frozenset[Permission]:
    """Unknown roles intentionally contribute no authority."""
    return frozenset(permission for role in roles for permission in ROLE_PERMISSIONS.get(role, ()))
