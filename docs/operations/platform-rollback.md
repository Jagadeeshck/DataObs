# Platform rollback

## Detection
Upgrade verification failure and compatibility-contract result.

## Impact
Treat dependency state as unhealthy unless explicitly fail-open telemetry; bound API and worker effects.

## Prechecks
Confirm exact release SHA, environment, synthetic marker, scoped target, security mode, timestamps, and current ownership/migration state.

## Mitigation
Rollback application only when metadata proves forward-schema compatibility; otherwise return rollback_blocked_by_migration.

## Recovery
Recover the dependency/state, wait for bounded probes, and resume gradually without retry amplification.

## Verification
Check `/livez`, `/readyz`, API and worker smoke, tenant isolation, release identity, checkpoints, alerts, and retained report checksums.

## Rollback
Use only the documented compatibility contract. Keep forward migrations; isolate the target if verification fails.

## Escalation
Escalate to Team 0 and dependency/security owners with timestamps, exact SHA, topology and redacted evidence.

## Retained evidence
Retain scenario report, logs/metrics, topology, tool versions, JUnit, scenario hash, redaction report and SHA-256 checksums.

## Prohibited actions
Never destructively reverse migrations or force an incompatible application.
