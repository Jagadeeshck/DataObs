from urllib.parse import quote

from .security import validate_endpoint


class SchemaRegistryClient:
    def __init__(self, config, transport):
        validate_endpoint(str(config.base_url), config.allowed_hosts)
        self.config = config
        self.transport = transport

    def subjects(self):
        return self.transport.get("/subjects", timeout=self.config.timeout_seconds)

    def versions(self, subject):
        return self.transport.get(f"/subjects/{quote(subject, safe='')}/versions", timeout=self.config.timeout_seconds)

    def schema(self, subject, version):
        return self.transport.get(
            f"/subjects/{quote(subject, safe='')}/versions/{quote(str(version), safe='')}",
            timeout=self.config.timeout_seconds,
        )

    def compatibility(self, subject):
        return self.transport.get(f"/config/{quote(subject, safe='')}", timeout=self.config.timeout_seconds)

    def check_compatibility(self, subject, version, transient_schema):
        """Ask the registry to evaluate a schema without changing registry state.

        Callers must not log ``transient_schema``. The bounded body is passed
        directly to the read-only compatibility endpoint and is not retained.
        """
        from packages.streaming.schema_intelligence import MAX_SCHEMA_BYTES, fingerprint_schema

        # Canonicalization also enforces the hard request-size ceiling. Only the
        # digest is safe for caller telemetry; this method deliberately returns
        # the provider response without adding the submitted material.
        fingerprint_schema(transient_schema)
        return self.transport.post(
            f"/compatibility/subjects/{quote(subject, safe='')}/versions/{quote(str(version), safe='')}",
            json={"schema": transient_schema},
            timeout=self.config.timeout_seconds,
            max_request_bytes=MAX_SCHEMA_BYTES,
        )
