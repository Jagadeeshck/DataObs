import re

SUPPORTED_SERVER_SERIES = ("11.8", "11.4")
DRIVER_REQUIREMENT = "mariadb==1.1.14"


def validate_product(version: str, version_comment: str = "") -> str:
    identity = f"{version} {version_comment}".lower()
    if "mariadb" not in identity:
        raise RuntimeError("server_product_mismatch")
    match = re.match(r"^(\d+\.\d+)", version)
    if not match:
        raise RuntimeError("server_product_mismatch")
    return match.group(1)
