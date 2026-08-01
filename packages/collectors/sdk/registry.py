from __future__ import annotations

import re
from collections.abc import Callable

from .base import IntegrationProvider

_PROVIDER_TYPE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")


class ProviderRegistry:
    """Explicit factory registry: no user-controlled imports or global mutable state."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], IntegrationProvider]] = {}
        self._metadata: dict[str, tuple[str, object]] = {}

    def register(self, factory: Callable[[], IntegrationProvider]) -> None:
        provider = factory()
        if not _PROVIDER_TYPE.fullmatch(provider.provider_type):
            raise ValueError("provider_type must be a stable lowercase identifier")
        if not _VERSION.fullmatch(provider.provider_version):
            raise ValueError("provider_version must be semantic version format")
        if provider.provider_type in self._factories:
            raise ValueError(f"provider already registered: {provider.provider_type}")
        capabilities = provider.capabilities()
        self._factories[provider.provider_type] = factory
        self._metadata[provider.provider_type] = (provider.provider_version, capabilities)

    def create(self, provider_type: str) -> IntegrationProvider:
        try:
            return self._factories[provider_type]()
        except KeyError as exc:
            raise KeyError(f"unknown provider: {provider_type}") from exc

    def provider_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def descriptions(self) -> dict[str, tuple[str, object]]:
        return {key: self._metadata[key] for key in sorted(self._metadata)}
