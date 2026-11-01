---
name: release-triage
description: Diagnose exact GitHub CI failures and assign shared or domain ownership without hiding skipped tests.
---
# Release Triage

1. Capture SHA, workflow, job, step, actual error/log and artifact.
2. Group identical root-cause errors; avoid 20 duplicate fixes for one shared issue.
3. Classify: Team 0 platform/release, Team 1 streams/pathways, Team 2 data, Team 3 incidents, Team 4 providers, Team 5 Console.
4. Reproduce smallest failing command in correct environment; preserve exact dependency versions.
5. Fix owned source plus regression, run focused suite, then producer + independent verifier.
6. Record evidence status by exact SHA/run/attempt, skipped count and remaining blockers.
**Output:** root cause table, patch plan, test list, ownership and go/no-go impact.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
