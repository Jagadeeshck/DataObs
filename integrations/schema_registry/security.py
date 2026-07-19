from urllib.parse import urlparse


def validate_endpoint(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.hostname not in allowed_hosts:
        raise ValueError("Schema Registry endpoint is not an allowlisted credential-free HTTPS URL")
