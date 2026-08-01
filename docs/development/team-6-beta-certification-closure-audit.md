# Team 6 Beta certification closure audit

## Audited baseline and repository truth

The supplied checkout had no configured Git remote, so the latest resolvable `main`
state is the supplied merged-main HEAD,
`232a8e073cbfedf0d0c2444e9be23b59e959a4ee`. This is the immutable starting and
audited release base. The executable terminal is obtained only from
`packages.elastic_store.manifest.migrations()[-1].migration_id`; at audit time it is
`0022_aws_data_platform_collector`. The pre-change certification manifest and release
workflow instead named `0021_lineage_analysis_explorer`. The AWS workflow shortened
the terminal to `0022`. Several capability workflows also retained `0021` after
overlapping security merges.

## Candidate workflow and artifact inventory

All entries below support exact-SHA checkout through `workflow_dispatch`. `push` is
accepted only where the manifest explicitly permits it. A standard artifact contains
exactly one `evidence.json` envelope; older supporting reports remain subordinate.

| Team | Capability | Workflow | Artifact | Beta | Standard envelope before closure |
|---|---|---|---|---|---|
| 6 | identity/security | `beta-security-hardening.yml` | `beta-security-hardening-evidence` | mandatory | no |
| 6 | deployment packaging | `beta-deployment-packaging.yml` | `beta-deployment-packaging-evidence` | mandatory | partial |
| 6 | backup/restore | `beta-backup-restore.yml` | `beta-backup-restore-v1-evidence` | mandatory | new/yes |
| 1 | stream observer | `stream-observer-backend.yml` | `stream-observer-backend-v1-evidence` | mandatory | metadata only |
| 1 | pathway intelligence | `pathway-intelligence-backend.yml` | `pathway-intelligence-backend-v1-evidence` | mandatory | no |
| 1 | stream 360 | `stream-360-core-console.yml` | `stream-360-core-console-v1-evidence` | mandatory | no |
| 1 | cluster 360 | `cluster-360-console.yml` | `cluster-360-console-v1-evidence` | mandatory | no |
| 1 | connector/schema 360 | `connector-schema-360-console.yml` | `connector-schema-360-console-v1-evidence` | mandatory | no |
| 1 | pathway explorer | `pathway-explorer-console.yml` | `pathway-explorer-console-v1-evidence` | mandatory | no |
| 2 | quality monitoring | `data-quality-monitoring.yml` | `data-quality-monitoring-v1-evidence` | mandatory | metadata only |
| 2 | quality Console | `data-quality-console-v1.yml` | `data-quality-console-v1-evidence` | mandatory | metadata only |
| 2 | job/run backend | `job-run-backend.yml` | `job-run-backend-evidence` | mandatory | metadata only |
| 2 | lineage Console | `lineage-analysis-console.yml` | `lineage-analysis-console-evidence` | mandatory | metadata only |
| 3 | incident workbench | `incident-workbench-certification.yml` | `incident-workbench-v1-evidence` | mandatory | new/yes |
| 4 | integration SDK | `integration-sdk-certification.yml` | `integration-sdk-v1-evidence` | mandatory | new/yes |
| 4 | AWS collector | `aws-data-platform-collector-v1.yml` | `aws-data-platform-collector-v1-evidence` | optional | partial |
| 5 | Console experience | `console-product-experience.yml` | `console-product-experience-v1-evidence` | mandatory | delegated legacy |

The release assembly artifact is
`team-6-beta-security-release-certification-v1-evidence`. It is deliberately not an
input capability, avoiding a circular dependency.

## Defects and selected changes

Snapshot CLI calls omitted required `--url` while passing unsupported repository
arguments. Elasticsearch lacked `path.repo`; snapshot scope used broad wildcards; no
destructive two-tenant fingerprint proof existed. The corrected workflow registers
and verifies an in-container filesystem repository and the shared scope derives from
registered migration resources. The destructive integration test measures duration
without claiming RPO/RTO.

The old manifest mapped platform security to packaging, incidents to IAM, Integration
SDK to governance, and Team 5 to a reusable workflow artifact. The reconciled
manifest uses owned caller artifacts and separates security, packaging, resilience,
and release assembly. The orchestration model is **Model A / two phase**: validate and
dispatch every manifest workflow for the target SHA, then invoke candidate verification
and assembly only after artifacts exist.

Helm YAML had been written with a JSON suffix. Rendering now uses
`helm-rendered-production.yaml` and assertions use `helm-render-report.json`. Local
Kind scripts still require Docker, Kind, kubectl, Helm, runnable candidate images, and
sufficient cluster resources. Hosted restart, migration rerun, upgrade, rollback, and
post-rollback evidence remains mandatory and is not inferred from rendering.

The image inventory is API, Console, quality worker, scanner worker, monitor runtime,
pathway worker, and Kafka observer. Every matrix Dockerfile exists. Collection Manager,
POCs, Grafana Alloy, Elasticsearch, and an identity provider are excluded. SBOMs are
generated before login; critical vulnerability findings block; highs are retained in
machine-readable scanner output. No image was published in this audit.

## Hosted status and deferrals

GitHub CLI is unavailable and this checkout has no remote, so no exact-final-SHA
hosted workflow was dispatched. Run URLs, IDs/attempts, artifact IDs/checksums, image
scan results, deployment/rollback conclusions, and the independent final-artifact
verification are **pending**, not passing. Use:

```bash
git push -u origin codex/team-6-beta-certification-closure-v1
gh workflow run <manifest-workflow> --ref codex/team-6-beta-certification-closure-v1
gh workflow run beta-1-release-candidate.yml --ref codex/team-6-beta-certification-closure-v1 \
  -f target_sha=<final-40-character-sha> -f candidate_version=0.1.0-beta.1 \
  -f dry_run=true -f release_base_sha=232a8e073cbfedf0d0c2444e9be23b59e959a4ee
```

Incident correlation/flood control, a Job/Run Console without a focused owned workflow,
live AWS credentials/certification, and Collection Manager packaging are deferred.
AWS collection is optional. Historical audit documents legitimately retain their
then-current migrations; active product and release truth uses the executable terminal.
No Beta-certified or production-ready claim is made.

Local repository, release metadata, manifest, security, formatting, lint, typing, and
focused Python gates pass. The real Elasticsearch test is defined but skipped without
the destructive opt-in service. Helm, kubectl, Kind, and Docker are unavailable in the
supplied environment, so deployment commands are warnings rather than passes. Console
typecheck/lint/tests pass after repairing merge-selected unclosed JSX/CSS, but the
production build still fails on pre-existing Team 2 Quality Console API/export drift;
that capability implementation is not repaired by Team 6 and remains an ownership
blocker. Consequently the rehearsal remains pending.
