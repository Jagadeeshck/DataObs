from dataclasses import dataclass


@dataclass(frozen=True)
class SourceBinding:
    source_id: str
    tenant_id: str
    environment: str


class SourceAuthenticator:
    def __init__(self, bindings):
        self._bindings = bindings

    def authenticate(self, token: str) -> SourceBinding:
        binding = self._bindings.get(token)
        if not binding:
            raise PermissionError("invalid source credential")
        return binding
