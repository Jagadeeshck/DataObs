# Team 0 upgrade, rollback and HA rehearsal

The bounded Kind harnesses perform fresh install, restart, worker replacement, migration idempotency, upgrade from the immediately supported prior version, readiness, Helm rollback, post-rollback smoke and preservation checks. Evidence records chart versions, immutable image digests, migration count/terminal, readiness and restart details, upgrade/rollback durations and smoke result in `upgrade-rollback-report.json` and `ha-restart-report.json`.

No eligible previous certified version or hosted run is retained. Both mandatory results are **pending**, never pass.
