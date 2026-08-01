# Backup and restore

## Beta contract

Elasticsearch snapshot/restore is the authoritative backup mechanism for DataObs durable state. The Team 0 scripts include `dataobs-*` indices (including migration state) and `logs-dataobs.*` append-only streams and exclude cluster-global state. External provider state, OIDC configuration/secrets, Kubernetes Secrets, transient memory, container filesystems and third-party systems are not backed up.

Operators must provision a snapshot repository supported by their Elasticsearch deployment. The filesystem repository option is test/CI-only and requires `path.repo`; production should use an administrator-managed object-store repository. Credentials are supplied through Elasticsearch configuration/environment and are never command arguments or repository files.

Required privileges include cluster monitor, snapshot create/status/restore, repository management when the script creates the test repository, and read/restore access to the selected DataObs resources. Least-privilege repository creation should be separated from routine snapshot execution in hosted environments.

## Ordering

1. Quiesce or fence writers and record the exact terminal migration.
2. Run `backup_dataobs.py`; it checks connectivity and the dynamically resolved executable terminal migration, registers the optional test repository, waits for the named snapshot, and emits a redaction-safe report.
3. Test restores only in an isolated recovery cluster. Close/delete conflicting target resources according to Elasticsearch restore requirements.
4. Run `restore_dataobs.py`, then run migrations forward if the restoring binary has a newer compatible terminal migration.
5. Verify document counts and deterministic tenant fixtures, cross-tenant denial, append-only streams, current projections, aliases/transforms, and application reads before reopening writers.

Restore must never downgrade mappings or edit a released migration. A snapshot newer than the running binary's supported terminal migration must not be opened.

## Limitations

The scripts verify snapshot/shard completion and terminal migration; the hosted workflow must additionally seed two tenants and verify isolation, append-only streams and projections after destructive restore. Until that retained exact-commit report exists, backup/restore is **implemented, locally validated where tests pass, and pending hosted validation**. RPO and RTO are unvalidated and no production recovery objective is claimed.
