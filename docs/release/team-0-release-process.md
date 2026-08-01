# Team 0 production release authority v1

## Contract and rename

**Team 0 — Platform, Security and Release** is the canonical active identity. The Beta 1 schema remains `1.0`; `compatibility_aliases` in the certification manifest is the only permitted Team 6 name mapping. A canonical and legacy upload is ambiguous unless the mapping permits coexistence and their decoded evidence envelopes are byte-identical. Historical audits retain Team 6 facts.

## Exact-SHA process

1. Dispatch `team-0-release-candidate.yml` with a 40-character SHA, SemVer candidate, audited base SHA, bounded retention and timeout.
2. The read-only job verifies target/base/main ancestry, migrations, generated files, boundaries, ledger, metadata, manifest, Team 0 naming and merge markers.
3. Required producers come only from the manifest. `dispatch_beta_certification.py` records dispatch/run/attempt/timestamps/conclusion/artifacts, polls with three-attempt API retries, and cancels known runs on timeout.
4. Exact-SHA envelopes are downloaded with archive size/path limits and rejected for wrong repository, workflow, SHA, migration, schema, category, run or attempt, duplicates, ambiguity, expiration and failed/pending status.
5. Independent verification generates `release-decision.json`; status prose is downstream output and cannot override evidence.
6. Only a non-dry-run, fully passing candidate can enter the protected `production-release` environment. That job alone receives package/content writes and OIDC.

## Publication and supply chain

Build, lint, render, SBOM, provenance and critical-vulnerability enforcement precede authentication. Images and charts use immutable digests. The protected job publishes Helm OCI, keylessly signs and attests the digest, then verifies the signature and provenance identity. The existing image matrix follows the same scan-before-login boundary. Dry run never reaches registry login, signing, tags, releases or environments.

## Current truth

Implementation and local static tests are distinct from hosted certification. No hosted exact-SHA producer bundle, secured Elasticsearch/OIDC run, destructive recovery run, registry digest, signature or measured operation evidence is retained for this change. The decision is therefore **NO_GO**. Embedded Elasticsearch, an embedded identity provider, Collection Manager, demos and POCs remain excluded.
