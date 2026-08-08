# Restore verification failure

## Detection
Count/fingerprint, migration, IAM, API, worker, security or tenant-isolation mismatch.

## Impact
Treat dependency state as unhealthy unless explicitly fail-open telemetry; bound API and worker effects.

## Prechecks
Confirm exact release SHA, environment, synthetic marker, scoped target, security mode, timestamps, and current ownership/migration state.

## Mitigation
Keep target isolated, retain evidence, investigate scope, and repeat into another clean disposable target.

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
Never expose the failed target, waive tenant isolation, or modify evidence.
