import re

DRIVER_REQUIREMENT = "mssql-python>=1.13,<1.14"
SUPPORTED_MAJOR_VERSIONS = {16: "SQL Server 2022", 17: "SQL Server 2025"}


def validate_product(version: str, product: str = "Microsoft SQL Server") -> int:
    if "sql server" not in product.lower() or not (match := re.match(r"^(\d+)\.", version)):
        raise RuntimeError("server_product_mismatch")
    major = int(match.group(1))
    if major not in SUPPORTED_MAJOR_VERSIONS:
        raise RuntimeError("unsupported_server_version")
    return major
