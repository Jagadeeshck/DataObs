# Team 2 data intelligence runtime

Migration 0029 establishes storage contracts only after doctor confirms an unambiguous 0001–0028 chain. All writers must derive tenant/environment from trusted runtime context, use deterministic document IDs, bounded reads, OCC for projections, and create-only immutable evidence.

The current merged repository still lacks dedicated Lineage and Data Contract worker CLIs and the complete Data Contract/adaptive API and Console closure described in the reconciliation assignment. Those surfaces must not be advertised as production-ready. Existing adaptive evaluation runs through the monitor runtime; do not introduce another scheduler. Operators should use existing monitor health telemetry and the non-destructive migration doctor. Historical collision handling is documented in [Team 2 migration reconciliation](team2-migration-reconciliation.md).
