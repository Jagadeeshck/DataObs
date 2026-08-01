# Team 0 destructive backup and restore certification

The authoritative commands remain `scripts/operations/backup_dataobs.py` and `restore_dataobs.py`. The isolated harness must explicitly opt in, derive registered snapshot resources (never use an unbounded wildcard), seed tenant A/B production/test fixtures, capture counts and stable per-resource fingerprints, snapshot timestamps and terminal migration, destroy/isolate originals, restore, and compare inventory, counts, fingerprints, tenant/environment, append-only and policy resources.

`backup-restore-report.json` records measured backup/restore duration and fixture data-loss window; these measurements are not contractual RPO/RTO. No hosted destructive run is retained, so the mandatory result is **pending** and publication is blocked.
