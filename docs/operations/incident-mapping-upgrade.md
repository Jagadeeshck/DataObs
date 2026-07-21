# Incident and finding mapping upgrade runbook

## Before the upgrade

1. Stop or drain incident writers and confirm Elasticsearch cluster health is yellow or green.
2. Take and verify a repository snapshot containing `dataobs-findings-v1`, `dataobs-incidents-v1`, their aliases, and `dataobs-system-migrations-v1`. **Do not proceed without a restorable snapshot.**
3. Confirm both concrete indices exist, their read/write aliases resolve only to the expected v1 index, and their mappings have `dynamic: strict`.
4. Export redacted mapping and alias snapshots. Never include document payloads, credentials, or authorization headers in artifacts.

```bash
./bin/dataobs elastic status
./bin/dataobs elastic plan > incident-migration-plan.json
curl -fsS "$ELASTICSEARCH_URL/dataobs-findings-v1,dataobs-incidents-v1/_mapping" > pre-upgrade-mappings.json
curl -fsS "$ELASTICSEARCH_URL/_alias/dataobs-findings-v1-*,dataobs-incidents-v1-*" > pre-upgrade-aliases.json
```

Inspect plan entry `0012_incident_mapping_and_occ_fix`: it may target only the two concrete v1 indices. An absent index, non-strict mapping, or incompatible existing field is a stop condition, not permission to auto-create or relax mappings.

## Apply and verify

```bash
./bin/dataobs elastic apply
./bin/dataobs elastic status
curl -fsS "$ELASTICSEARCH_URL/dataobs-findings-v1,dataobs-incidents-v1/_mapping" > post-upgrade-mappings.json
curl -fsS "$ELASTICSEARCH_URL/_alias/dataobs-findings-v1-*,dataobs-incidents-v1-*" > post-upgrade-aliases.json
```

Confirm status is ready, 0012 has one applied record, both mappings remain strict, and aliases still select their original concrete index. Perform tenant-scoped smoke writes using synthetic, non-sensitive maximal Finding and Incident documents through the service API. Update the incident using returned OCC metadata and verify replay of the same finding leaves its occurrence count unchanged.

## Monitor

Monitor redacted counts for HTTP 409 responses and Elasticsearch version-conflict exceptions. A short burst under concurrent ingest is expected because the service retries; sustained 409s indicate retry exhaustion or writer contention. Never log raw queries, documents, credentials, or Elasticsearch exception bodies.

## Failure recovery

If apply fails, keep writers drained. Verify 0012 is absent from the migration state. Existing documents and aliases should remain usable because mapping addition happens in place and alias cutover is not involved. Correct a missing-index operational error only by restoring the snapshotted concrete index; do not allow auto-creation. Correct transient cluster errors, then rerun the identical migration.

An incompatible existing type cannot be repaired by changing 0012 or loosening strict mappings. Escalate to a separately reviewed v2-index migration with controlled reindex validation and atomic alias cutover. Preserve the v1 indices and snapshot throughout.

Mapping additions are not destructively rolled back. For application rollback, drain writers, deploy the prior binary only if it can safely read the expanded mapping, and retain all indices and aliases. Otherwise remain on the fixed writer and forward-repair. **Deleting incident or finding indices is never a normal rollback procedure.**
