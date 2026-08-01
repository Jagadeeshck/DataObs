# Beta 1 release rehearsal

1. Select a full commit SHA reachable from `main` and a version such as `0.2.0-beta.1`.
2. Confirm all mandatory Team 1–5 workflows completed for that exact SHA and retained their uniquely named evidence.
3. Dispatch **Team 0 Beta 1 release candidate** with `dry_run=true`.
4. Review every report status, checksum, producer SHA, workflow identity, terminal migration, environment version, SBOM and vulnerability summary. Pending is not passing.
5. Exercise Kind restart/upgrade/rollback and isolated snapshot restore. Mandatory skips fail certification and must be resolved before promotion.
6. Repeat from the same immutable SHA after evidence defects are corrected only when rerun ambiguity has been explicitly resolved; never copy evidence from an older SHA.
7. Keep this workflow dry-run-only. Publication is a separate future task requiring explicit approval; this rehearsal has no publish job.
8. Verify registry digests against the candidate manifest, rehearse Helm upgrade and rollback compatibility, and retain provenance/evidence according to policy.

Abort on missing evidence, ambiguous runs, schema/version/migration mismatch, critical vulnerability, unpinned image, secret exposure, route-policy drift, restore failure or cross-tenant access. A successful dry run is a release-candidate rehearsal, not a production certification.
