# Job event replay

Pause projection consumers, select OpenLineage evidence by tenant, environment, and a bounded time range, then replay in `(source_event_time, event_id)` order into empty current projections. Preserve event IDs and fingerprints. Exact duplicates are safe; fingerprint conflicts must stop replay for investigation. Compare counts and terminal states before switching readers, and retain the prior projection snapshot for rollback.
