# Team 5 upgrade compatibility Console v1 evidence

- Team: Team 5
- Repository: Jagadeeshck/DataObs
- Audited base SHA: `ad31a9a38d69dd98b2191318b331a7134f5339e4`
- Workflow: `.github/workflows/team-5-version-upgrade-compatibility-console-v1.yml`
- Compatibility API: present; policy release state is `unvalidated`
- Upgrade-readiness API: present; requires target
- Migration DAG: valid, 33 nodes in audited validator output
- Terminal derivation: validator reports `0033_team1_stream_schema_intelligence_runtime`; canonical helper is blocked by existing `NameError`
- Helm consistency: skipped/blocked by the same helper error
- Compatibility, predecessor, rollback, NO_GO, stale evidence, partial failure, permission, privacy and no-execution: covered by Console tests/workflow
- Accessibility, Playwright, build, bundle and performance: workflow gates; local results are not preclaimed
- Warning: this UI evidence does not certify or support an upgrade and is not deployment evidence
