from __future__ import annotations

from services.monitoring.providers.base import ObservationProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ObservationProvider] = {}

    def register(self, monitor_type: str, provider: ObservationProvider) -> None:
        if monitor_type in self._providers:
            raise ValueError(f"provider already registered: {monitor_type}")
        self._providers[monitor_type] = provider

    def resolve(self, monitor_type: str) -> ObservationProvider:
        try:
            return self._providers[monitor_type]
        except KeyError as exc:
            raise LookupError(f"unsupported monitor type: {monitor_type}") from exc

    @property
    def ready(self) -> bool:
        return bool(self._providers)
