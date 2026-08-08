# Team 0 hosted core platform certification v1 audit

## Audit identity and truth

This audit was performed before changes against the clean local `main` commit
`d006339a3989dc7d2062f1df3f11a908732b093f`. No `origin` remote is configured in
the supplied checkout, so that commit cannot be independently asserted to be the
latest GitHub `main`. This is a blocking hosted prerequisite, not a reason to
weaken ancestry checks.

> `framework_exists != certification_completed`

No hosted credentials, protected GitHub environment, Kubernetes context, OIDC
issuer, Elasticsearch endpoint, snapshot repository, retained upgrade release,
or prior hosted artifact is available in this checkout. Consequently the current
release decision is **NO_GO**, the support matrix remains empty, and all hosted
results are **PENDING**. Local tests, workflow YAML and rendered templates are not
certification evidence.

## Version and release inventory

| Item | Audited value | Source / observation |
|---|---|---|
| Terminal migration | `0029_team2_data_intelligence_reconciliation` | `python scripts/release/current_terminal_migration.py` (registry-derived) |
| Helm chart / DataObs app | `0.2.0` / `0.2.0` | `helm/dataobs/Chart.yaml` |
| Elasticsearch target | `9.4.2` | certification manifest and support matrix |
| Kubernetes range | `>=1.30.0-0 <1.31.0-0` | chart `kubeVersion` |
| Release decision | `NO_GO` | current release process/status; no exact-SHA hosted evidence |
| Supported platforms | none | `supported: []` |
| Candidate platform | Kubernetes 1.30.x, ES 9.4.2, Python 3.13, Node 22 | unvalidated matrix entry |
| HA profiles | `development`, `standard-ha`, `production-ha`: unvalidated | scale/HA audit and validator catalog |
| Capacity profiles | `small`, `medium`, `large`: unvalidated | scale/HA audit and scenario catalog |

The production values use external authenticated Elasticsearch over HTTPS with
certificate verification and secret references; external OIDC issuer/audience/
client configuration; multi-tenancy; non-root pods; read-only filesystems;
capability drops; service accounts without token automount; NetworkPolicies;
PDBs; probes; topology spread; and digest-shaped image pins. These are packaging
contracts only. The values' embedded `terminalMigration` was stale (`0021`)
versus the executable registry (`0029`) and is reconciled by this branch before
any hosted run.

## Reusable machinery

| Area | Existing implementation | Audit conclusion |
|---|---|---|
| Scale / HA | `.github/workflows/team-0-production-scale-ha-certification-v1.yml`, `scripts/performance/certification_phase.sh`, `verify_scale_certification.py` | Exact-SHA, bounded harness exists; no retained hosted result. |
| Dependency resilience / DR | `.github/workflows/team-0-dr-dependency-resilience-certification-v1.yml`, `scripts/resilience/certification_phase.sh`, `safety_guard.py`, `verify_dr_certification.py` | Fault/upgrade/restore contract exists; protected driver and evidence absent. |
| Release certification | `.github/workflows/team-0-release-candidate.yml`, dispatch/verification/release-decision scripts | Authority is fail closed; dry run only is appropriate here. |
| OIDC / security | `tests/security/test_oidc_rbac_tenant.py`, IAM/security workflow, certification security runner | Local security coverage exists; no disposable issuer conformance artifact. |
| Privileged / credentials | Team 0 privileged-access workflow and lifecycle tests | Reusable, but hosted disposable credential lifecycle is unexecuted. |
| Backup / restore | `scripts/operations/backup_dataobs.py`, `restore_dataobs.py`, Beta backup/restore workflow | Manifest-scoped snapshot tooling exists; no disposable repository/result. |
| Migrations | executable registry, current-terminal script, doctor/status/apply tooling, immutability tests | Registry terminal is 0029; no clean hosted apply/repeat evidence. |
| Evidence | scale and DR independent validators, certification artifact redactor/verifiers, release authority | Validators are reusable; producer status alone is insufficient. |
| Production Helm | `helm/dataobs/values-production.yaml`, chart assertions, lint/render workflows | Production contract exists; runtime deployment is unexecuted. |

## Hosted prerequisites

Repository-available prerequisites are the chart, safety guards, bounded scenario
catalogues, migration/backup tooling, evidence schemas, redaction utilities and
independent validators. Externally required and currently missing prerequisites
are:

* a configured `origin` and a demonstrably latest clean `main`;
* protected environment `team-0-hosted-certification-test` and an ephemeral,
  non-production multi-node Kubernetes context with TTL/resource ownership labels;
* secured Elasticsearch 9.4.2 endpoint, CA and protected credentials, plus a
  disposable snapshot repository;
* disposable OIDC Authorization Code + PKCE S256 issuer/client/test identities;
* TLS ingress/DNS, an OTLP fault target, and protected infrastructure driver;
* an actual retained previous DataObs release compatible with the candidate;
* registry-readable exact-SHA images, workload driver credentials, and artifact
  retention/independent-verifier access.

Owners: Team 0 Platform supplies cluster/Elasticsearch/snapshot/cleanup inputs;
Team 0 Security supplies OIDC identities and secret references; Team 0 Release
selects the retained source release and candidate SHA. Exact values belong in
protected configuration, never in the repository.

## Documentation freshness

`docs/development/production-readiness-audit.md` is historical and stale, as are
earlier Team 0 scale/HA and DR audits with older base SHAs and migrations. They
remain immutable historical records. `docs/release/current-production-readiness.md`
is the active fail-closed view for this effort.
