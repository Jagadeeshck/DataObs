# Beta 1 certification

Beta certification is an exact-commit evidence decision, not a branch label or local test result. `beta-1-certification-manifest.yaml` identifies each capability owner, workflow, unique artifact, required conclusion/schema/version/test categories, and whether absence blocks Beta.

`verify_beta_candidate.py` accepts only one completed successful `workflow_dispatch` run from the correct repository/workflow at the target SHA, with the exact non-expired artifact name. It independently validates producer SHA, evidence schema, Elasticsearch version, terminal migration, test summaries and tool metadata. Missing or ambiguous mandatory evidence fails; optional exclusions remain pending and never pass silently.

The dispatch-only candidate workflow checks out the exact SHA, runs repository/security/Console/Helm/recovery gates, verifies capability evidence, builds without pushing, generates SBOMs, scans critical vulnerabilities before registry authentication, and uploads redaction-safe evidence. Only the separate protected `publish` job receives content/package/OIDC write permissions and only when dry-run is false and all dependencies pass.

Implemented and local validation are distinct from hosted validation. Beta-supported status requires the full successful candidate run and retained artifact at the exact release SHA. This foundation does not declare Beta 1 certified and does not declare production readiness.
