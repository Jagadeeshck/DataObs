# Team 1 streaming schema production runtime v1 audit

## Baseline and dependencies

The audited repository head was `96d6e4fc0e20d11ee7dcaca5f681660d5dd2be52`. The checkout has no configured
Git remote, so `git fetch origin` and a comparison with a newer remote `main` were not possible. The local history
contains merge commits for PR #257 (`96d6e4f`), PR #256 (`141ec42`) and the Team 5 presentation PR #261 (`d47985d`).
PR #257 added the transient, bounded schema evaluators and privacy contract, but did not add durable runtime storage.
PR #256's product-impact implementation remains the authoritative product traversal and is not duplicated here.

The terminal migration derived by `scripts/release/current_terminal_migration.py` before changes was
`0031_team3_post_incident_review_analytics`. Existing migrations include Team 2 reconciliation, Team 1 multi-broker
runtime and Team 3 review analytics. Migration doctor could not connect because Elasticsearch was not running locally.
The forward-only decision is therefore `0032_team1_stream_schema_intelligence_runtime`; no released migration changed.

## Existing product surface

`StreamRepository` and `stream_routes.py` already own `/api/v1/schema-subjects` plus versions, changes, impact and
evidence subresources. Stream 360 currently reads an embedded schema projection from `dataobs-kafka-schemas-v1-read`.
The production runtime intentionally retains that namespace. A later API projection adapter can switch those reads to
the new evidence stores without introducing another schema product.

Stream Intelligence already supplies deterministic identities, append-only create semantics, real Elasticsearch
`_seq_no`/`_primary_term` OCC, fenced leases and persistence-before-checkpoint ordering. The schema repository/runtime
reuse those patterns. Pathway history/traversal and `packages/pathways/product_impact.py` remain authoritative; this
change persists bounded resource and consumer bindings that those adapters can consume without a second graph engine.

## Storage and privacy decision

Existing Stream 360 mappings cannot truthfully contain compatibility evidence, application bindings, exposure
transitions and runtime fencing state. Migration 0032 adds five strict current projections and four append-only data
stream contracts. Repository methods reject schema bodies, payloads, samples, keys and exceptions. Only fingerprints,
counts, hashed field identities, reason codes and bounded references may cross the persistence boundary.

The runtime writes version evidence, version projection, compatibility evidence, structural changes, subject
projection, resource/application bindings, consumer-impact transition and current impact, in that order. It advances
the checkpoint only after all work completes. Deterministic IDs make replay converge after a partial failure.

## Truthfulness and limitations

An incompatible registry result plus a bound consumer is only `potentially_exposed`. `incompatible` requires a known
supported-version mismatch; `degradation_observed` requires independent schema-error evidence. No causal or RCA claim
is emitted. Registry compatibility and Team 2 contract compliance stay separate.

This local change does not claim hosted certification. Elasticsearch 9.4.2 vertical-slice, scale, Console,
Pathway/Data Product query-adapter, Playwright and axe evidence remain unverified and capabilities must remain
`functional_unvalidated` until exact-SHA hosted evidence exists.
