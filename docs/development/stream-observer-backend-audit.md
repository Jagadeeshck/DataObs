# Kafka Stream Observer backend audit

The branch starts at merge `8643d10`, which contains PRs #177, #178, and #179. The released migration registry terminates at `0021_lineage_analysis_explorer`; migrations 0009 and 0010 already provide the fixed Stream 360 projections, evidence streams, leases, and checkpoints, so no migration is added.

## Gaps found and disposition

The existing observer collected a single Admin inventory on one interval, used an in-memory checkpoint in production, nested canonical values under `document`, and reported unconditional readiness. Connect and Schema Registry commands were placeholders. Although bounded offsets, lag velocity, drain time, retention risk, replication health, a binding registry, and lease primitives existed, they were not composed.

Backend v1 composes independently scheduled inventory, group, offset, Connect, and Schema Registry capabilities. Production construction uses the Elasticsearch checkpoint and lease resources; documents use deterministic tenant/environment scoped IDs and canonical top-level fields. Optional HTTP providers report `not_configured` without failing Kafka inventory. Existing helpers remain authoritative, with retention output aligned to the public safe/warning/at-risk vocabulary.

## Deliberate boundaries

The collector never reads message payloads, never performs Connect restart actions, and does not implement Kinesis or remediation. Topic configuration is limited to the existing allowlist. Connect stores summaries and fingerprints rather than complete configurations; Schema Registry stores fingerprints and structural summaries rather than raw schemas.

