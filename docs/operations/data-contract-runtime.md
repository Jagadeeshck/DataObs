# Data contract runtime

The runtime is designed for bounded polling with fenced leases, monotonic checkpoints, overlap replay and deterministic writes. A cycle verifies Elasticsearch and migrations, claims work, reads changed evidence, resolves the historically effective version, appends evaluation/violation evidence, updates health, resolves recovered violations, and only then advances its checkpoint. Partial writes do not advance checkpoints.
