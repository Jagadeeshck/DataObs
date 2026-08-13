# Team 0 unified release authority — 2026-08-13

## Factual preflight

The starting checkout was `6a5acaa7c4f6a37298fc90d2044db120a93f5072`. It had no configured Git remote,
and `gh auth status` reported no authenticated host, so latest-main freshness, Actions history, permissions, rulesets,
and required checks could not be verified. The executable terminal migration was
`0033_team1_stream_schema_intelligence_runtime`. The final branch SHA is the commit containing this document.

## Authority and ordering

The old tag workflow queried only CI and two Data Product workflows through the legacy verifier. That verifier is now
explicitly non-authoritative. `Team 0 Beta 1 release candidate` is the sole certification producer: it applies the Beta
capability manifest's exact-SHA, artifact, producer, category, Elasticsearch, and migration checks, then requires the
security release gate to be `PASS` and a non-empty certified platform before emitting `dataobs-release-authorization`.
The tag workflow rejects missing or ambiguous successful producer runs and validates the artifact against the tag SHA,
workflow run, repository, current executable migration, security state, certification state, and platform.

```text
mandatory capability evidence
           |
           v
verify Beta certification
           |
           v
security PASS
           |
           v
release authorization artifact
           |
           v
build
           |
           v
SBOM + vulnerability scan
           |
           v
publish
```

Registry authentication follows authorization, build, SBOM generation, and the critical-vulnerability check. Migration
range endpoints are derived from executable registry JSON. Production (`vX.Y.Z`), Beta (`vX.Y.Z-beta.N`), and RC
(`vX.Y.Z-rc.N`) tags are accepted; other spellings fail closed. Same-workflow checksum validation is artifact integrity,
not independent verification. GitHub-hosted CI likewise is not hosted-product or independent certification.

## Current decision and administration

The product truth remains **NO_GO**: security is **INCOMPLETE**, supported platforms are `[]`, hosted tested is `0`, and
independently verified is `0`. No synthetic passing fixture changes those facts. An administrator must configure and run
Actions, retain **Team delivery foundation** as the stable required integration workflow, configure rulesets/checks, and
obtain hosted product, supported-platform, and independent signature evidence. Local tests cover pass/fail security,
exact SHA, platform, tag semantics, ambiguity, ordering, dynamic migration metadata, and the single-authority contract.
