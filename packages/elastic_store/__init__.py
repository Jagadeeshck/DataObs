"""Elasticsearch storage package with a dependency-free metadata boundary.

Release and certification tooling imports :mod:`packages.elastic_store.manifest`
to discover migration metadata.  Importing that pure module must not eagerly load
the Elasticsearch client, which is a runtime-only dependency.  Runtime entry
points remain available from this package through lazy attribute resolution for
backwards compatibility.
"""

from typing import Any

from .manifest import DATA_STREAMS, MIGRATION_STATE_INDEX, MUTABLE_INDICES

_RUNTIME_EXPORTS = ("apply", "plan", "rollback", "status")


def __getattr__(name: str) -> Any:
    if name in _RUNTIME_EXPORTS:
        from . import registry

        return getattr(registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DATA_STREAMS", "MIGRATION_STATE_INDEX", "MUTABLE_INDICES", *_RUNTIME_EXPORTS]
