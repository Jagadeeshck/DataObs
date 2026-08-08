import hashlib


def stable_stream_id(tenant_id: str, environment: str, system: str, cluster_id: str, native_id: str) -> str:
    value = "\x1f".join((tenant_id, environment, system, cluster_id, native_id))
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_messaging_id(
    *,
    tenant_id: str,
    environment: str,
    messaging_system: str,
    provider_account_scope: str,
    region_or_location: str,
    namespace: str,
    resource_kind: str,
    provider_resource_id: str,
) -> str:
    """Return a collision-resistant provider-neutral resource identity.

    Display names are deliberately excluded as an identity source.  Empty scope
    components are retained so identities remain stable as optional metadata is
    enriched.
    """
    parts = (
        "messaging-v1",
        tenant_id,
        environment,
        messaging_system,
        provider_account_scope,
        region_or_location,
        namespace,
        resource_kind,
        provider_resource_id,
    )
    return "msg_" + hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
