from typing import Protocol

from .models import RemediationEpisode


class EffectivenessRepository(Protocol):
    def put(self, episode: RemediationEpisode) -> RemediationEpisode: ...

    def for_incident(
        self, tenant_id: str, environment: str, incident_id: str, *, limit: int = 100
    ) -> list[RemediationEpisode]: ...
