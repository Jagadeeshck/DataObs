# Team 0 post-recovery release rebaseline v1 audit

Audit time: 2026-10-12 UTC. This is an active baseline record, not hosted certification or publication authority.

## Repository and candidate

| Fact | Audited value |
|---|---|
| Latest fetched `origin/main` | `2281a64034b915f4f7dd556cd582f27e30660a1c` |
| Candidate | `2281a64034b915f4f7dd556cd582f27e30660a1c` |
| Parents | `1ac6f84b654b31161c5f90fa9840f369e14152a9`, `109732e2ceb0ea8dd71b268ca0b14c171b5ccd11` |
| Tree | `a54609a7e449ae7c03341630f2445a94c008aa1c` |
| Starting tree | clean |
| Application / chart | `0.2.0` / `0.2.0` |
| Executable terminal migration | `0033_team1_stream_schema_intelligence_runtime` |
| Migration graph | valid, 33 migrations, one terminal leaf |
| Elasticsearch server target / Python client | `9.5.5` / `elasticsearch[async]==9.4.1` |
| Hosted CI Python / Node / pnpm | Python `3.12` (Foundation), Node `22`, pnpm `10.28.1` |
| Local audit Python / Node / pnpm | Python `3.14.4`, Node `24.15.0`, pnpm `10.28.1` |
| Security posture / security gate | `INCOMPLETE` / `INCOMPLETE` |
| Release authority | `NO_GO` |
| Supported platforms | `[]` |

The candidate is the latest fetched main commit, is unambiguous and reachable from `origin/main`, and has deterministic
migration and release metadata. PR #295 is merged at this commit. Its head `109732e...` is a parent, but evidence from
that head is not transplanted: only runs whose `head_sha` is the merge candidate are indexed.

## Current policy state

Active critical findings are `SECF-002` (hosted tenant isolation absent) and `SECF-003` (independent signature
verification absent). `SECF-001` remains resolved. There are no active security exceptions. Compatibility is
`compatible_but_unvalidated` for declared initial interfaces; supportability and operational readiness remain
unvalidated because exact-SHA archive inspection, hosted recovery and support-contract certification are incomplete.
The active release-gate matrix contains historical `PENDING` entries and is not manually promoted by this audit.

## GitHub and retained evidence discovery

The public GitHub API was queried without credentials. Candidate runs discovered include:

| Capability | Run | Workflow result | Artifact |
|---|---:|---|---:|
| Foundation backend and Console | `38270882312` | PASS | `11756264084`, `11757171571` |
| IAM/RBAC repository security | `38270882222` | PASS | `11757410721` |
| Integration SDK | `38270882323` | PASS | `11756298823` |
| Incident workbench | `38270882287` | PASS | `11756572510` |
| RabbitMQ | `38270882262` | PASS | none retained |
| Data Quality Console | `38270882209` | FAIL | `11756384104` |
| Backup/restore | `38270882084` | FAIL | none |
| CI supply-chain aggregate | `38270882113` | FAIL | SBOM artifact `11757071513` |

Foundation job metadata confirms compileall, Ruff, Black, mypy, pytest, migration immutability, release checks, Console
frozen install/generation/typecheck/lint/format/unit/build/bundle/performance/audit all passed. Its Playwright and
accessibility steps were skipped, so browser and accessibility remain pending. IAM executed repository security tests
and Compose configuration only; it is not hosted disposable IdP/OIDC/TLS conformance. RabbitMQ passed but retained no
artifact. Public API access exposes metadata but artifact downloads require authentication (`401`), so **zero archives
were independently inspected** and none are labeled `INDEPENDENTLY_VERIFIED`. Full entries and expiration times are in
`evidence/team-0-post-recovery/evidence-index.json`.

Open release-relevant PRs were #296 (GCP Pub/Sub and CI hygiene) and #291 (Vitest 4.1.11). PR #292 is closed and
superseded; it was not merged. PR #291 remains open and must be separately rebased/validated rather than folded into this
baseline. PR #296 is outside this frozen candidate.

## Truthful domain outcomes

* Tenant isolation: local adversarial tests are useful but no exact-candidate hosted suite covers the required CRUD,
  search, admin, integration, diagnostics, role-binding and lifecycle boundary; `SEC-TENANCY-001` is not hosted verified.
* OIDC/TLS: IAM PASS does not establish hosted issuer/audience/JWKS/signature/expiry/negative cases, rotation, PKCE,
  outage recovery or certificate validation.
* Kubernetes/Helm: local lint/render policy may pass, but no inspected exact-candidate running-cluster artifact exists.
* Kafka: the reported strict `dataobs-findings-v1` incompatibility around `retry_count` and `tags` has no passing
  exact-candidate hosted artifact. It remains a Team 1 cross-team blocker; Team 0 did not edit migrations, mappings, or
  indices.
* Browser/accessibility: Foundation explicitly skipped them. Neither category is converted to PASS.
* Backup/restore/DR: the candidate backup workflow failed and no destructive disposable restore or true DR evidence is
  available. Simulations are not promoted.
* Scale/HA: no profile has complete exact-SHA hosted evidence.
* Supply chain: an SBOM archive is discoverable, but the aggregate workflow failed and no complete verified
  vulnerability/license/provenance/signature chain exists.

## Stale documents and governance

`docs/release/beta-1-rc1-target.md`, older certification audits, and retained root reports describe historical candidates
and are not rewritten or consumed as current evidence. The active production-readiness renderer now points at this
candidate. Foundation wrapper job IDs are uniquely named `foundation-backend` and `foundation-console`; after this
change emits checks once, an administrator must select the emitted Foundation contexts in the `main` ruleset, require
both without bypass, and remove ambiguous generic contexts. Repository code does not change branch protection.

## Conclusion

The exact candidate is well-defined and Foundation checks passed, but discovery metadata is not archive verification.
Mandatory hosted security, Kubernetes, browser/accessibility, recovery/DR, Kafka and supply-chain gates remain
incomplete or failed. The supported-platform decision remains `[]`; security remains `INCOMPLETE`; release authority is
`NO_GO`; no publication occurred.
