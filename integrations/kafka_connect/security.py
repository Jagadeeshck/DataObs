import ipaddress
from urllib.parse import urlparse


def validate_endpoint(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.hostname not in allowed_hosts:
        raise ValueError("Kafka Connect endpoint is not an allowlisted credential-free HTTPS URL")
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
        if address.is_loopback or address.is_link_local or address.is_private:
            raise ValueError("private Connect endpoints require an explicitly isolated adapter")
    except ValueError as exc:
        if "private Connect" in str(exc):
            raise
