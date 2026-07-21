import yaml  # type: ignore[import-untyped]

MAX_BYTES = 1_000_000


def parse(text: str):
    if len(text.encode()) > MAX_BYTES:
        raise ValueError("monitor YAML exceeds 1 MB")
    if any(token in text.lower() for token in ("password:", "secret:", "raw_sql:")):
        raise ValueError("secrets and raw SQL are forbidden")
    value = yaml.safe_load(text)
    if not isinstance(value, dict) or not isinstance(value.get("monitors"), list) or len(value["monitors"]) > 500:
        raise ValueError("invalid or unbounded monitor document")
    return value
