# Lineage rebuild

1. Stop lineage projection transforms and writers.
2. Snapshot `dataobs-lineage-current-v1` and `dataobs-column-lineage-current-v1`.
3. Retain both append-only observation streams.
4. Clear only the current projections, reset the lineage checkpoint, and replay observations in `observed_at` order.
5. Verify tenant/environment counts, deterministic edge IDs, strict mappings, transform lag, and bounded traversal samples before resuming writers.

Rollback stops the 0021 transforms and restores projection snapshots. Evidence streams must not be deleted.
