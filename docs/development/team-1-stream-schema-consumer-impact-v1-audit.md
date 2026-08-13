# Team 1 stream schema consumer impact v1 audit

## Preflight

The audited baseline is `141ec426bef2f168996df122655b9bf2cb395ff7`. Fetching `origin` was attempted but the supplied checkout had no configured remote and GitHub required credentials; the baseline is the repository's merge of PR #256. That merge contains the prior **Stream-to-Data-Product Impact & Business Criticality v1** capability, so this change reuses its public pathway/product context and does not recreate traversal.

The dynamically reported terminal migration is `0030_team1_multi_broker_messaging_runtime`. No migration is added: existing bounded Stream 360 schema projections and evidence reads are sufficient for the v1 domain/API contract work. Migration doctor requires a running Elasticsearch service and is recorded as an environment-limited validation.

Inspected foundations include migrations 0009/0010, Team 1 migrations 0023/0025/0026/0028/0030, Team 2 reconciliation 0029, `packages/streaming/contracts.py`, Schema Registry client/collector/normalizer, Kafka observer runtime, Stream 360 routes/repository, pathway history/topology, reliability and intelligence runtimes, Team 2 Data Contracts/change gates, shared visualization primitives, and Investigation evidence contracts.

## Audit matrix

| Capability | Existing owner | Current implementation | Reusable | Gap | Decision |
| --- | --- | --- | --- | --- | --- |
| Schema collection | Team 1 | bounded Schema Registry collector, fingerprints and summaries | yes | no compatibility endpoint adapter | add read-only adapter |
| Compatibility rules | Team 2 / Team 1 boundary | Team 2 table rules; minimal streaming rules | primitives only | format semantics | pure Team 1 evaluator |
| Schema history | Team 1 | bounded Stream 360 versions | yes | safe change contract | extend domain, no new store |
| Producer binding | Team 1 | application observations | yes | schema usage contract | add pure binding contract |
| Consumer binding | Team 1 | groups/applications | yes | accepted versions often absent | retain unknown |
| Pathway impact | Team 1 | bounded topology and product-impact public API | yes | schema overlay | normalized domain evidence |
| Data Contract context | Team 2 | public reads | yes | none | read only, separate dimension |
| Data Product context | Team 2 | Team 1 public impact adapter over approved context | yes | none | reuse, never infer absent evidence |
| Incident overlay | Team 3 | incident read context | read only | none | never set severity/RCA |
| Investigation UI | Team 5 | normalized evidence contract/primitives | yes | schema evidence shapes | backend-derived evidence |

## Findings and decisions

* Kafka plus configured Schema Registry is functional/partial. Other brokers remain unsupported unless authoritative external metadata is present.
* The collector is bounded to 1,000 subjects and 100 versions. Evaluation history is capped at 25.
* Raw schema material is transient. Durable results contain fingerprints, counts, categories, and salted path hashes only. A legacy top-level schema name was removed from the semantic summary.
* Provider compatibility is preferred, followed by provider result, local format-specific evaluation, heuristic, then unavailable. Local results state their limitation and are never marked authoritative.
* Data Contract compliance and registry compatibility remain independent. Team 1 performs no Team 2 private writes.
