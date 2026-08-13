import re

DRIVER_REQUIREMENT = "oracledb>=4.0.2,<4.1"


def validate_product(version: str) -> str:
    # Branding and numeric releases intentionally remain separate; features are probed by dictionary shape.
    if not re.match(r"^\d+(?:\.\d+)+$", version):
        raise RuntimeError("unsupported_server_version")
    return version
