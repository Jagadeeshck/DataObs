import hashlib


def fingerprint(schema: str) -> str:
    return hashlib.sha256(schema.encode()).hexdigest()
