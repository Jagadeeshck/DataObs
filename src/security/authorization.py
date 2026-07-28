from .errors import SecurityError
from .models import Principal
from .permissions import Permission


def authorize(principal: Principal, permission: Permission) -> None:
    if permission not in principal.permissions:
        raise SecurityError("permission_denied", "Required permission is not granted", status_code=403)
