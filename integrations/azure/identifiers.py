import re
from urllib.parse import urlsplit

RG = re.compile(r"^[\w().-]{1,90}$", re.ASCII)
SERVICE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{2,62}$")
STORAGE = re.compile(r"^[a-z0-9]{3,24}$")
FILESYSTEM = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{3,63}(?<!-)$")


def _valid(value, pattern):
    if not isinstance(value, str) or not pattern.fullmatch(value) or ".." in value or any(ord(c) < 32 for c in value):
        raise ValueError("invalid Azure resource identifier")
    return value


def resource_group(v):
    return _valid(v, RG)


def service_name(v):
    return _valid(v, SERVICE)


def storage_account(v):
    return _valid(v, STORAGE)


def filesystem(v):
    return _valid(v, FILESYSTEM)


def path_prefix(v, maximum_depth=32):
    if (
        not isinstance(v, str)
        or not v
        or len(v) > 1024
        or v.startswith("/")
        or "?" in v
        or "#" in v
        or "\\" in v
        or any(p in ("", ".", "..") for p in v.split("/"))
        or urlsplit(v).scheme
        or len(v.split("/")) > maximum_depth
    ):
        raise ValueError("invalid ADLS path prefix")
    return v


def synapse_endpoint(name):
    return f"https://{service_name(name)}.dev.azuresynapse.net"


def datalake_endpoint(name):
    return f"https://{storage_account(name)}.dfs.core.windows.net"
