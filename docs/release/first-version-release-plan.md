# DataObs 0.2.0 first-version release plan

**Assessment date:** 2026-10-27  
**Audited main SHA:** `b39a66d1546feba70de84aa6d8c9956e5892d16d`
**Decision:** `NO_GO` — this is a plan, not release authorization.

The current machine-readable Gate 0 inventory is
[`v0.2.0-gate-0-blockers.yaml`](v0.2.0-gate-0-blockers.yaml). It records the
first meaningful error, owner, workflow run, expected evidence artifact, local
resolution, and hosted-verification state without freezing a candidate.

## Executive assessment

DataObs has a credible **local evaluation MVP** and a substantial automated
validation surface, but it does not yet have the exact-commit, independently
verified evidence required for a supported first release. The application and
chart versions are already `0.2.0`, the migration graph is valid with terminal
migration `0033_team1_stream_schema_intelligence_runtime`, and the local demo
path is reproducible. Those facts establish a useful release *candidate input*;
they do not establish a releasable artifact.

The authoritative product truth remains:

| Field | Current value |
| --- | --- |
| Application / chart | `0.2.0` / `0.2.0` |
| Release | `NO_GO` |
| Security | `INCOMPLETE` |
| Supported platforms | `[]` |
| Elasticsearch server | `9.4.2` |
| Terminal migration | `0033_team1_stream_schema_intelligence_runtime` |
| Published GitHub releases/tags | none observed at assessment time |

## What is ready now

- The first-MVP Compose path builds, migrates, seeds, checks readiness, verifies
  tenant isolation, and exercises the Console-to-API proxy. It is explicitly an
  evaluation environment rather than a supported installation.
- The migration graph, release metadata, and Helm migration metadata agree on
  the current terminal migration.
- The latest audited main run passed Integration SDK, Incident Workbench,
  Google Pub/Sub, and RabbitMQ validation. The Team Delivery Foundation backend
  and Console jobs also passed.
- Release schemas, a protected exact-SHA authority path, evidence envelopes,
  supply-chain expectations, rollback policy, and a first-platform
  certification workflow already exist. The release work should finish those
  mechanisms rather than invent a parallel release process.

## Why 0.2.0 cannot be released today

1. **The candidate is not frozen.** The active readiness document and
   first-platform candidate still reference an older SHA, while current main is
   `b39a66d1546feba70de84aa6d8c9956e5892d16d`. Evidence from different commits
   must not be combined.
2. **Packaging is red.** Main run `40578796841` passes Helm lint, every supported
   profile render, chart assertions, and migration immutability, then fails at
   the mandatory Kind smoke. Its retained artifact is `12768123785`; the
   protected, digest-pinned smoke configuration is still required.
3. **Security and Pathway are red.** Security run `40578796917` and Pathway run
   `40578796828` both fail while applying released migrations. The retained
   artifacts are `12769625480` and `12769396466`. Team 0 must inspect the
   authenticated migration log and reproduce the shared clean-install failure
   before Team 1 changes domain code. Released migrations and incompatible
   indices remain untouched.
4. **The hosted demo proof is absent.** The MVP workflow was not triggered for
   the infrastructure-only merge and must be dispatched on the next Gate 0 SHA.
5. **Recovery evidence is red.** Backup/restore run `40578797192` completes the
   destructive proof, then fails while generating exact-commit evidence. Its
   retained artifact is `12768706830`. Public job metadata does not expose the
   authenticated artifact contents, so Team 0 must inspect the retained
   inventory and envelope log rather than guess the underlying error.
6. **Security and platform authorization are incomplete.** Hosted OIDC/TLS,
   adversarial tenant isolation, Kubernetes runtime security, independent
   artifact signature verification, browser/accessibility acceptance, and one
   supported platform profile remain unproven for one frozen commit.
7. **No immutable distribution exists.** There is no Git tag or GitHub release,
   and no approved image/chart digest set, SBOM, provenance, signature, or
   publication decision for 0.2.0.

## Next item: Team 0 first-version candidate closure

The next delivery item should be narrowly titled:

> **Team 0: close 0.2.0 release-candidate infrastructure blockers**

It should fix only shared release infrastructure in this order:

1. reproduce and repair the Helm lint failure in the deployment-packaging job;
2. reproduce the migration-apply failures against a clean Elasticsearch 9.4.2
   instance and determine whether they share one mapping/migration defect;
3. repair backup/restore evidence-envelope generation without weakening exact
   SHA, run-attempt, checksum, or independent-verification requirements;
4. rerun Team Delivery Foundation and First MVP demo smoke on the resulting
   commit; and
5. publish a refreshed blocker inventory for that exact commit.

This item must not nominate a release, change `NO_GO`, broaden platform claims,
or absorb unrelated feature work. If migration diagnosis confirms the known
Kafka findings mapping incompatibility, create a separate Team 1 additive
migration task; never rewrite a released migration or delete the index as a
workaround.

## Release sequence

### Gate 0 — stabilize main

**Exit criteria:** deployment packaging, secured migration application,
backup/restore evidence generation, Team Delivery Foundation, and First MVP
demo smoke pass on the same main commit. All failures have an owning team and a
first meaningful failure recorded. No mandatory job is skipped.

### Gate 1 — freeze `0.2.0-rc.1`

Choose one clean, reachable main SHA only after Gate 0. Record its audited base,
terminal migration, dependency/tool versions, and workflow run IDs. Dispatch
the existing exact-SHA release-candidate workflow in dry-run mode. Do not move
the candidate SHA after evidence collection begins; fixes require a new freeze
and a complete rerun.

### Gate 2 — certify one bounded platform

The first realistic target is the already documented small/development profile:
Kubernetes `1.30.x`, external secured Elasticsearch `9.4.2`, Python `3.13`,
Node `22`, external OIDC with Authorization Code + PKCE S256, and the packaged
components only. Embedded Elasticsearch, embedded identity, Collection Manager,
demos, and POCs remain excluded.

Required evidence for the frozen SHA includes:

- clean install, readiness, smoke, restart, and resource-policy checks;
- TLS Elasticsearch authentication and version enforcement;
- hosted OIDC/JWKS/PKCE failure and success paths;
- adversarial tenant A/B/C isolation;
- migration apply/idempotency and immutable registry checks;
- backup, destructive restore, recovery timing, and integrity checks;
- Console browser and accessibility acceptance without skips;
- SBOM and zero blocking vulnerability findings under repository policy; and
- immutable image/chart digests with provenance, signatures, and independent
  verification.

### Gate 3 — release authority review

Consolidate only producer artifacts matching the frozen SHA, workflow identity,
run attempt, terminal migration, schema version, and freshness window. The
independent verifier—not prose or a successful demo—must produce `GO`. Update
the supported-platform matrix from `unvalidated` only after this review.

### Gate 4 — publish and verify

Through the protected release environment, publish immutable container and
Helm OCI artifacts, create the signed `v0.2.0` tag and GitHub release, attach
checksums/SBOM/provenance, and verify installation using only published
digests. Run the rollback/recovery procedure appropriate to a first release and
record the support/incident handoff. Any digest, signature, provenance, or
post-publication smoke mismatch stops the release.

## Realistic target plan

Dates are exit-criteria targets, not promises:

The requested Friday 30 October 2026 target is feasible only as a conditional
release-candidate target: Team 0 shared infrastructure must merge first, each
domain team must then use an independent branch from updated main, and every
mandatory workflow must be rerun on the final integrated SHA. If those
conditions are not met by the Friday review, the release moves; the gates do
not.

| Target | Scope | Exit condition |
| --- | --- | --- |
| **27 Oct** | Team 0 shared triage | Authenticated artifacts reviewed; shared first errors reproduced |
| **28 Oct** | Shared fixes, then domain branches | Team 0 merges first; Teams 1, 2, and 5 submit focused fixes from updated main |
| **29 Oct** | Final-SHA Gate 0 rerun | All mandatory workflows pass without skips on one integrated SHA |
| **30 Oct** | Conditional candidate review | Freeze `0.2.0-rc.1` only if Gate 0 and independent evidence verification are green |
| **After GO** | Publication | `v0.2.0` artifacts, tag, release notes, signatures, and clean-install verification are complete |

If Gate 0 is not green by Day 1, keep the demo available as an evaluation MVP
and move the release date; do not reduce the release gates. If hosted
certification exposes product defects, return ownership to the relevant team
and freeze a new SHA after fixes.

## Operator checklist

Before candidate freeze:

```bash
git fetch origin
git status --short
git rev-parse HEAD
git merge-base --is-ancestor HEAD origin/main
python scripts/release/validate_migration_graph.py
python scripts/release/current_terminal_migration.py --json
python scripts/release/check_release_metadata.py
python scripts/release/check_helm_migration_consistency.py
./scripts/deployment/chart_assertions.sh
```

Before the demo or release rehearsal:

```bash
./scripts/demo_mvp.sh config
./scripts/demo_mvp.sh up
./scripts/demo_mvp.sh verify
./scripts/demo_mvp.sh status
```

Stop immediately on a dirty candidate checkout, mixed SHAs, missing evidence,
skipped mandatory checks, credential leakage, cross-tenant data, or a failed
independent verification. The local demo is never evidence for production
security, resilience, or supported-platform certification.
