import re

SUPPORTED_SERVER_SERIES = ("8.4", "9.7")
DRIVER_REQUIREMENT = "mysql-connector-python>=26.7,<26.8"


def validate_product(version: str, version_comment: str = "") -> str:
    identity = f"{version} {version_comment}".lower()
    if "mariadb" in identity:
        raise RuntimeError("server_product_mismatch")
    match = re.match(r"^(\d+\.\d+)", version)
    if not match:
        raise RuntimeError("server_product_mismatch")
    return match.group(1)
