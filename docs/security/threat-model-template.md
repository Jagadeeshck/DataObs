# DataObs threat model template

## Scope
Define the subsystem, exclusions, owner, version, and review date.
## Assets
List protected product and operational assets.
## Trust boundaries
Reference IDs in `trust-boundaries.yaml` and add justified subsystem boundaries.
## Identities
List human, workload, provider, and recovery identities.
## Entry points
List API, event, administrative, deployment, and diagnostic entry points.
## Data classifications
Reference `data-classification.yaml`; do not reproduce secret values.
## Threats
Describe actor, precondition, action, impact, and detection.
## Mitigations
Map concrete implementation safeguards to each threat.
## Residual risks
Record unmitigated risk and accountable owner without claiming acceptance.
## Controls
Reference stable `SEC-*` IDs.
## Evidence
Name authoritative exact-SHA or environment-bound artifacts.
## Assumptions
State deployment and external-service responsibilities.
## Open risks
Link findings or time-bounded approved exceptions.
