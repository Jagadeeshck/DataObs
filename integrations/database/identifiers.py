import re

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,127}$")


def validate_identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("invalid_configuration")
    return value


def quote_identifier(value: str, quote: str = '"') -> str:
    return f"{quote}{validate_identifier(value)}{quote}"
