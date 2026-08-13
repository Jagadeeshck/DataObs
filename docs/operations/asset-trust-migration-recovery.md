# Asset Trust migration recovery

Never edit or renumber a released migration. Run migration doctor and checksum
verification, establish the actual terminal migration, and only then allocate the
next forward-only Team 2 migration. Reapplying it must be idempotent.

After an Elasticsearch interruption, restore connectivity, allow leases to expire,
and let a new worker claim with a higher fence. Replay is safe because historical
evaluation IDs are deterministic; current projection updates must reject an old
fence. Do not delete history during recovery.
