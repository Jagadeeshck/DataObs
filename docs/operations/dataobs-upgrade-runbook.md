# DataObs upgrade runbook

1. Rebase on latest main and run the compatibility gate.
2. Run readiness preflight; stop for every blocker or unknown required fact.
3. Create and validate a recent manifest-scoped backup using the existing recovery runbook.
4. Enter maintenance, apply the certified chart/image by digest, and run migrations through the existing migration job.
5. Verify terminal migration, readiness, smoke evidence, and known issues.
6. Record exact-SHA evidence and exit maintenance. Do not execute the advisory plan automatically or copy secrets.
