import re

_FORBIDDEN = re.compile(r"[\x00-\x1f\x7f]|--|/\*|\*/|;|\"")


def validate_identifier(value: str, *, maximum_length: int = 255) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum_length or _FORBIDDEN.search(value):
        raise ValueError("unsafe SQL identifier")
    return value


def quote_identifier(value: str) -> str:
    """Quote a discovered identifier; embedded quotes are rejected, not escaped."""
    return f'"{validate_identifier(value)}"'
