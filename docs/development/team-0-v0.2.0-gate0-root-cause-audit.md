# Team 0 v0.2.0 Gate 0 root-cause audit

Assessment: 2026-10-28. Base main: `09fa1fe615c69f79a8056772a4b424b5c564fb86`.
Decision: **GATE_0_BLOCKED / NO_GO**. No candidate frozen or release authorized.

This initial audit precedes repairs. GitHub run metadata, jobs, attempts, logs and
artifact inventories were read using existing platform authentication. PRs
#305–#308 and their changed-file inventories were reviewed. Earlier example runs
40583053660/54504/54431/53969/54361 are PR runs with head
`194aeb375a70140052d9d92511417f16ffb911c5`; their executed merge SHA may differ.
They must not be combined with main evidence. All current-main runs below are
attempt 1 and source `09fa1fe615c69f79a8056772a4b424b5c564fb86`.

| Class / owner | Workflow / run / job | First failing step and actual error | Root cause / cascade | Repair / required evidence / state |
| --- | --- | --- | --- | --- |
| STALE_GENERATED_ARTIFACT / Team 0 | ci.yml / 40583121862 / Documentation truth gate (122467505456) | Validate and render capability source of truth: generated docs differ | Google Pub/Sub source metadata changed without canonical rendered docs; also fails Python and incident-automation suites | Run canonical renderer twice; retain regression guard and exact-SHA hosted results. Open. |
| TEAM0_SECURITY_PLATFORM / Team 0 | ci.yml / 40583121862 / Python quality and unit tests (122467504777) | Unit tests: scanner asset flow asserts 403 == 201 | Test requests tenant t1 without authorized principal context; production tenant isolation correctly rejects it | Repair bounded test identity, retain negative authorization assertion; no auth weakening. Open. |
| TEAM0_SHARED_CI / Team 0 | ci.yml / 40583121862 / Certification contracts (122467505093) | actionlint: SC1036 malformed command substitution; 23 shell findings | Shared workflow shell syntax/hygiene | Fix real defects with shellcheck enabled; actionlint across all workflows and hosted proof. Open. |
| TEAM0_SHARED_CI / Team 0 | ci.yml / 40583121862 / Terraform and Helm validation (122467505365) | Terraform validate roots/modules: Invalid character / Invalid single-argument block | Semicolon-packed HCL in platform outputs/variables | Canonical HCL; fmt and credential-free init/validate all supported roots/modules. Open. |
| DOMAIN_TEAM_DEFECT / Team 3 | ci.yml / 40583121862 / Incident migration and OCC gate (122467505129) | Focused quality checks: mypy datetime minus None, set(object), recurrence/automation typing | Incident-manager domain typing; not separate infrastructure failures | Team 3 handoff, no exclusions or product repair by Team 0. Blocked. |
| TEAM0_SECURITY_PLATFORM / provisional Team 0 | beta-security-hardening.yml / 40583121854 / security (122467503915) | Apply existing migrations: Incompatible existing mapping on dataobs-data-products-v1: description, owner, revision, tags | Shared global mapping union may create Data Products index with unrelated domain types; requires clean secured ES reproduction and ownership decision | Compare released mappings and registry creation; never edit released migration or relax compatibility. First/second apply + checksums required. Open. |
| TEAM0_PACKAGING / Team 0 | beta-deployment-packaging.yml / 40583122158 / validate (122467505001) | Kind smoke: DATAOBS_SMOKE_VALUES unset | Workflow provides absent protected configuration; Kind itself starts. Independent-verification then lacks evidence.json | Build immutable disposable candidate images and real test ES; retain clean install/uninstall diagnostics. Open. |
| TEAM0_RELEASE_EVIDENCE / Team 0 | beta-backup-restore.yml / 40583122138 / certify (122467504553) | Generate exact-commit backup and restore evidence: missing or empty evidence/results/backup-restore.json | **The preceding pytest step says 1 skipped, not a completed destructive test.** Same historical symptom in 40578797192; its artifact 12768706830 includes JUnit and inventory but no JSON. Inspect skip governance before treating this as a path-only defect | Fix actual producer execution and enforce non-skipped JUnit + semantic recovery report; execute isolated real recovery. Open. |
| TEAM0_SECURITY_PLATFORM / Team 0 | first-mvp-demo-smoke.yml / 40583122195 / smoke (122467504993) | Build/start/seed/verify: same data-products mapping conflict | Cascades from shared migration failure | Rerun after migration repair; evaluation sanity only. Blocked. |
| TEAM0_RELEASE_EVIDENCE / Team 0 | ci.yml / 40583121862 / Certification summary (122470212599) | DATA_PRODUCT_CERTIFICATION_PROFILE must be explicit | Summary invoked without required profile; mandatory certification jobs skipped following failures | Inspect documented ownership and profile contract; never count skips as success. Open. |
| TEAM0_RELEASE_EVIDENCE / Team 0 | active readiness and team-0-release-gates-v1.yaml | Historical candidate SHA values | Active view renderer reads stale candidate source; gate source references another historical SHA | Use canonical renderers without freezing RC or manually flipping evidence-derived gates. Open. |

Foundation run 40583122211: backend job 122467505294 and Console job
122467505851 passed. This is base evidence only; both must rerun on final SHA.
Prior reviewed artifacts include 12770509076 (migration log), 12769673769
(packaging), 12770503415 (MVP diagnostics), 12768706830 (recovery),
12769819755/12769394384 (Foundation). IDs are historical, not final-candidate proof.

## Validation and ownership follow-up

Pending implementation, clean secured Elasticsearch reproduction, exact-SHA hosted
reruns, retained canonical evidence and independent verification. Every mandatory
skip, missing artifact, mixed SHA or unexplained failure keeps Gate 0 blocked.

## Repair findings and current limits

- Canonical capability rendering changes only the three current generated product
  documents; a second render after committing them has zero diff. Source Pub/Sub
  metadata matches the implemented Team 4 provider and tests.
- Scanner contract test now uses an explicitly scoped collection identity with
  COLLECTION_MANAGE, INTEGRATIONS_WRITE and ASSETS_READ only. Cross-tenant access
  and IAM mutation are explicitly denied; production authorization is unchanged.
- All workflows pass actionlint with ShellCheck. No global ignore was added.
- All ten Terraform roots/modules initialize with backend disabled and validate.
  Provider compatibility warnings remain in legacy AWS/Grafana modules. No apply
  was performed; generated provider lockfiles were removed from the checkout.
- Mapping ownership is **Team 0 registry selection**, not a requested Team 2
  schema change: 0007 first creates dataobs-data-products-v1 using the runtime
  global union. Released 0015 explicitly defines description=text, owner=object,
  revision=integer, tags=keyword. Unrelated global contracts had preempted those
  names. Creation now selects the first explicit field definitions for each
  concrete index, preserving subsequent conflict checks. Released 0031–0033 use
  strict mapping wrappers rather than bare property dictionaries; the shared
  registry now normalizes both released shapes with explicit strict validation.
  Regression checks compare every explicit released mapping to index creation.
  All 33 migration checksums remain unchanged. Actual first/second clean apply
  is still required; static compatibility is not a substitute.
- Local Elasticsearch 9.4.2 image pull succeeds, but a newly created container
  exits during native bootstrap: `Could not set coredump filter`, caused by
  missing `/proc/self/coredump_filter`. This is EXTERNAL_ENVIRONMENT. It blocks
  local secured migration, MVP, Kind and recovery execution; no TLS/native-safety
  bypass was introduced. Hosted disposable-runner execution is required.
- Packaging now prepares a disposable registry with real manifest digests for
  exact-SHA API/Console builds and an authenticated test ES on the Kind network.
  The HTTP-only registry/ES profile is explicitly bounded smoke, not TLS security
  certification. Other workers are explicitly disabled in that bounded profile.
  A separate security runner uses authenticated HTTPS Elasticsearch with a local
  test CA, verifies anonymous rejection and performs both migration applications.
  Console chart nginx points to the release's API Service and has writable /tmp
  over a read-only root. Common ES username/store settings match runtime names.
- Backup failure is execution, not a fabricated path-only recovery: the global
  integration opt-in was missing. Both opt-ins are now set; the actual recovery
  test writes SHA, snapshot/deletion/restore/integrity/isolation results and
  timing. Validation rejects skipped/empty/malformed JUnit, wrong SHA/version,
  failed restore, missing integrity and missing timing. No live recovery success
  or timing is claimed until that test actually executes on supported runtime.
- New signed-JWT tests retrieve real HTTPS JWKS and exercise issuer, audience,
  signature, expiry, rotation, malformed keys and TLS trust/hostname failures.
  Explicit tenant selectors are denied correctly. **Three stronger tests fail**:
  signed tenant A can list/search/delete tenant B's legacy `/rules` data without
  selecting B. `get_stores` returns one application StoreBundle and legacy rule
  handlers never apply request tenant context. This is a Team 2 domain handoff;
  the regression tests remain enabled and failing, keeping security/Gate 0 red.
  This is confirmed in memory mode; durable-store isolation remains unproven.
  Diagnostic/support HTTP routes are absent in the inspected OpenAPI surface;
  no unsupported route coverage is claimed.
- Team 3 scoped mypy reproduces 20 errors in nine incident-manager files.
  `mypy src` passes. No domain code or mypy exclusion was changed.
- The current readiness and release-gate renderers retain NO_GO, no frozen
  candidate and no supported platforms. Historical candidate documents remain
  historical. The Gate 0 coordinator reuses the canonical envelope and existing
  Beta independent verifier plus actual supporting-file hashes and attempt-specific
  mandatory job checks. It cannot authorize publication.

Final-head hosted results, workflow URLs and artifact IDs belong in the retained
Gate 0 verification artifact, generated after committing. The tracked inventory
records exact observed base runs; it does not invent a self-referential commit
SHA or relabel base evidence as final-head proof.
