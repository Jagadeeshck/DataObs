# Disaster recovery

## Detection
Declared incident, dependency validation and loss of registered DataObs resources.

## Impact
Treat dependency state as unhealthy unless explicitly fail-open telemetry; bound API and worker effects.

## Prechecks
Confirm exact release SHA, environment, synthetic marker, scoped target, security mode, timestamps, and current ownership/migration state.

## Mitigation
Use a clean target, correct release and scoped snapshot; record every manual timestamp and verify all state.

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
Never use wildcard deletion, restore unrelated indices, expose credentials, or claim a stronger rehearsal class.
