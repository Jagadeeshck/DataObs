# Incident ingestion semantics

## Stable identifiers

The incident identifier contract is **v1 and stable**:
`deterministic_id("incident", [tenant_id, deduplication_key])`. The deduplication key already contains tenant, environment, asset, finding type, monitor/policy identity, and the observation time bucket. Environment must not be added to the incident-ID inputs a second time. Any future ID change requires a versioned data migration and dual-read plan.

A finding ID represents source identity and schema version, not a particular observation. It includes tenant, environment, asset, finding and signal types, source event ID, and source event version. Consequently, corrected observations retain their finding ID.

## Pure merge table

| Input | Incident write | Occurrence | Projection |
|---|---:|---:|---|
| New finding ID | yes | +1 | sorted union of assets; newest evidence/time; deterministic severity |
| Exact replay | no | unchanged | unchanged |
| Newer replay | yes | unchanged | timestamp, evidence, summary and non-empty ownership refresh |
| Stale replay | no | unchanged | cannot regress timestamp, evidence, ownership, or severity |
| Stale replay with unknown asset | yes | unchanged | monotonic asset-set enrichment only |

Finding IDs and affected assets are unique and sorted. Equal-timestamp evidence correction uses a canonical deterministic ordering. Empty ownership never erases known ownership. The merge function returns a decision and never mutates its inputs.

## Concurrency

Elasticsearch is authoritative. A first writer uses the stable ID with `op_type=create`. A loser re-reads by tenant, environment, and deduplication key, recomputes the merge, and writes only if a mutation remains. Updates require `_seq_no` and `_primary_term`. After an update conflict the service repeats that same read/decide operation; if the winner already applied equivalent state, it returns without another write. Three failed attempts raise the redacted domain `VersionConflict`, mapped to HTTP 409; the finding has already been retained for reconciliation.

No lock is required. Old and new workers use the same v1 ID, so a rolling deployment converges through create/OCC conflicts rather than creating parallel incident documents.
