# Team 2 asset trust production-closure preflight

Date: 2026-08-13. Base: `ad31a9a`; PR #269 merge: `9c228b7f0b74009c0cdbf0799cde3c715217fa0e`.

## Audit

PR #269 delivered the canonical domain models, deterministic/versioned formula,
confidence and coverage, caps, attribution, memory/Elasticsearch persistence, and
the single `quality.asset_trust` ledger entry. Those contracts remain canonical.

Canonical projections owned by monitoring/monitor runtime, Data SLO, Data
Contracts, dbt intelligence, job reliability, schema intelligence, lineage, Data
Products, Findings, recommendations, and Change Gates overlap with trust only as
read-only evidence sources. Asset Trust must not parse provider payloads or redo
their evaluations. The new resolver therefore accepts narrow canonical reader
ports and retains source references and provenance.

The Asset API, Asset 360 console, signed cursor API, and shared navigation are
production integration points still requiring coordinated owners. No parallel
inventory or source-detail page is introduced here. Existing ETag/OCC repository
conventions are retained; the runtime follows bounded claims and monotonic fencing.

## Blockers and migration decision

The checkout has no configured `origin`, so latest-main fetch/rebase and hosted
exact-head verification cannot be performed. The terminal-migration helper also
fails because `migrations` is undefined in its module. Consequently no migration
number is guessed and no released migration is edited. Elasticsearch resources
already named by PR #269 have real repository readers/writers, but their registry
reconciliation remains blocked until the terminal migration can be established.

Capability status remains `functional_unvalidated`; promotion requires ES 9.4.2,
browser/axe, scale, and independent exact-head certification.
