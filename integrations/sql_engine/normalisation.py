from datetime import datetime, timezone


def observed_at() -> datetime:
    return datetime.now(timezone.utc)


def preserve_zero(value):
    return None if value is None else value
