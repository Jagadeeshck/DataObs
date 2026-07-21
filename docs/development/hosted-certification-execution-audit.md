# Hosted certification execution audit

Base revision: `b04e35fef909224d16f8a115052e737aed8e3e39` (merge of PR #109). PR #109 merged the PR #108 runtime contract work, but retained no successful hosted certification evidence. Migrations 0001–0012 remain immutable and are checked against the resolved pull-request base.

A file-presence test is not provider certification. Provider evidence requires a reachable provider plus an assertion on DataObs API or storage output.

| Area | Current implementation | Current evidence | Gap | Required hosted gate |
|---|---|---|---|---|
| GitHub Actions triggerability | PR, push, and typed dispatch | Workflow source | Repository settings unverified | Trigger `all`, retain run URL |
| workflow YAML validity | actionlint gate | Local parser/check | Hosted actionlint pending | Certification contracts |
| required job dependencies | Seven focused gates and explicit summary checks | Workflow graph | Hosted results pending | Summary |
| runner resource usage | Focused profiles, memory limits, `docker stats` | Per-job artifact design | Peak hosted values pending | Every provider gate |
| Compose profile membership | `cert-*` profiles; legacy aliases retained | Rendered configs | Hosted startup pending | Contracts and each job |
| image builds / service health | Pinned images and bounded health waits | Compose contracts | Hosted build timings pending | Relevant job |
| migration apply | Released CLI/mappings | Existing integration tests | clean/repeat/0011 upgrade evidence pending | Migrations/incidents |
| seed idempotency | deterministic console seeder | Local fixtures | full second-pass evidence pending | Provider jobs |
| PostgreSQL Scanner | explicit DB and file secret | vertical-slice tests | hosted API/storage evidence pending | PostgreSQL |
| Kafka brokers / Observer | three KRaft brokers and explicit observer config | live clients added | hosted inventory/checkpoint evidence pending | Kafka |
| Kafka Connect / Schema Registry | pinned services and HTTP clients | readiness assertions | recovery evidence pending | Kafka |
| OpenLineage | implemented ingest endpoint | real event client | storage remains limited by current implementation | OpenLineage/product |
| Asset/Pathway/Stream APIs | bounded live calls | API assertions | full journey depth pending | Product/browser |
| incident correctness | OCC integration suite | prior local evidence | hosted replay artifact pending | Migrations/incidents |
| OTel telemetry | pinned collector | live sink assertion | component coverage pending | Kafka/product |
| production Console / Playwright / axe | Nginx image and external config | browser suite | hosted report pending | Browser |
| security scenarios | fixtures, runtime suite, Trivy | local policy tests | IAM is shared/dev auth; SBOMs pending | Security |
| secret handling | ephemeral 0600 runtime file | contract tests | sentinel scan in hosted artifacts pending | All/summary |
| artifact collection | separate unflattened downloads | workflow definition | retained artifacts pending | Summary |
| redaction / manifest hashes | redact-before-hash and mutation verification | unit tests | hosted verification pending | Summary |
| hosted metadata | manifest reads GitHub environment | null locally | run ID/URL pending | Summary |
| capability promotion | reviewed proposal only | ledger remains blocked | no promotion without hosted success | Human review after run |

## Current conclusion

The repository now defines runner-safe execution, but **Phase B is not closed until the open draft PR has a successful retained hosted run**. Actions enablement, runner permission, and branch protection are external administrative facts and must not be inferred from YAML. Release readiness remains blocked.

> This hosted certification run validates only the named capabilities and dimensions. It does not make DataObs as a whole production-ready.
