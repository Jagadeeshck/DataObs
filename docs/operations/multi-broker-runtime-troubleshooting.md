# Multi-broker runtime troubleshooting

Run the migration doctor before enabling projection writers. A registry conflict is a hard stop; do not renumber released migrations. Inspect persisted runtime state by tenant and environment. Error codes are bounded and never contain raw exceptions.

On an OCC conflict, retain append evidence and enqueue reconciliation. A stale fencing token must be rejected. Replay the bounded evidence window to converge projections, relationships, and checkpoints. Checkpoints advance only after evidence and projections succeed. Missing Azure checkpoint evidence yields partial data with unknown lag; it must not be inferred from throughput.
