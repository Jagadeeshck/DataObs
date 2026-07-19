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
