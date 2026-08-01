"""Authoritative release metadata derived from executable repository state."""

from packages.elastic_store.manifest import migrations

ELASTICSEARCH_VERSION = "9.4.2"
REPOSITORY = "Jagadeeshck/DataObs"


def terminal_migration() -> str:
    """Return the terminal executable migration; never cache this in generated data."""
    registry = migrations()
    if not registry:
        raise RuntimeError("migration registry is empty")
    return registry[-1].migration_id


if __name__ == "__main__":
    print(terminal_migration())
