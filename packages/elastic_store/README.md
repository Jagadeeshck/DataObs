# Elasticsearch storage and migrations

`python -m packages.elastic_store.cli plan|apply|status|rollback` uses `argparse` to avoid adding a CLI framework dependency. The migration creates versioned mutable indices with read/write aliases and composable templates for append-only DataObs data streams. Runtime handlers check readiness instead of opportunistically creating mappings.
