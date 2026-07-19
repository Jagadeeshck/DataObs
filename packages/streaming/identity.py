import hashlib


def stable_stream_id(tenant_id: str, environment: str, system: str, cluster_id: str, native_id: str) -> str:
    value = "\x1f".join((tenant_id, environment, system, cluster_id, native_id))
    return hashlib.sha256(value.encode()).hexdigest()


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
