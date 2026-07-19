# Stream 360 product integration gate audit

Audit baseline: `f965d58` (the local merge commit for PR #97). The checkout has no configured Git remote, so the
baseline could not be fetched or compared with a hosted `main`. The merge subject explicitly records PR #97 as merged.
A protocol, contract, model, helper, or design document is not counted as an executable product capability.

| Capability | Current evidence | Remaining blocker | Implementation in this PR | Test evidence |
|---|---|---|---|---|
| PR #97 baseline | Local history contains merge `f965d58` for PR #97 | Hosted PR/CI state cannot be queried without a remote | Recorded the exact local baseline without overstating hosted state | `git log --all --merges` |
| Migration 0010 | It did not exist at the audit baseline; 0009 was latest | Observer indices named by repository code were not installed | Forward-only `0010_topic_queue_stream_360_completion` installs coordination/current indices, streams, and complete latest-transform definitions; 0001–0009 remain unchanged | Migration unit suite and plan validation |
| Checkpoints and leases | Repository referenced Kafka checkpoint/lease write aliases, but read/save paths also used the unrelated pathway checkpoint alias | Kafka aliases absent; inconsistent checkpoint alias made recovery unreliable | 0010 installs both resources and repository consistently uses the Kafka checkpoint aliases | Repository and migration tests |
| Kafka Observer entry point | `services/kafka_observer/cli.py` implements `run`, `collect-once`, `test-connection`, and `inventory`; service persists inventory | Required `offsets`, `groups`, `connectors`, `schemas`, `status`, durable run wiring, renewal and telemetry are incomplete | No completion claim; existing executable entry point was verified | Existing observer unit tests; real runtime pending |
| Kafka Admin collection | `ConfluentReadOnlyAdmin` calls metadata/config/group Admin APIs and emits brokers, topics, partitions and groups | Offset-watermark collection, bounded cluster-scale batching, quotas, and real three-broker evidence are absent | 0010 creates the required persistence targets; collection blocker remains | Unit tests only; real Kafka pending |
| Connect | REST client can list connectors/status and approval-gates a failed-task restart | No durable collector, connector restart lifecycle, audit, or recovery verification | No completion claim | Client unit tests only |
| Schema Registry | REST client lists subjects/versions; normalizer/diff/compatibility helpers exist | No complete Avro/JSON Schema/Protobuf collector or durable impact graph | No completion claim | Helper unit tests only |
| Persisted intelligence | Robust lag/velocity/drain/retention primitives and repository history exist from PR #97 | Full persisted-history execution and compacted-topic real evidence remain absent | Completion streams and current projections added | Unit tests; Elasticsearch integration pending |
| Product APIs | No required `/api/v1/streams`, cluster, consumer-group, connector, or schema route was found | Entire Elasticsearch-backed Stream product API surface is pending | No completion claim | Not run |
| Console routes | Console foundation exists, but none of the six required `/streams` routes was found | Inventory and five 360 experiences are pending | Repository generated-output policy prevents browser dependencies/builds from being committed | Not run |
| SSE | Shared application event facilities exist, but required Stream event names and replay/isolation evidence were not found | Stream event contract, bounded replay and tenant leakage tests pending | No completion claim | Not run |
| Shared monitor/incident/RCA | Shared systems and Kafka workflow foundations exist | Real Stream observation providers and end-to-end correlation evidence pending | No standalone Incident/Automation Workbench work was started | Unit foundations only |
| Real Kafka environment | No `docker-compose.stream-360-real-stack.yml` existed | Three brokers, Connect, Registry, OTel, producers/consumers and scenarios all pending | No completion claim | Not run |
| Playwright and axe | Console has Playwright configuration and an e2e spec | No recorded real-stack Playwright or axe execution evidence | Browser caches/results are explicitly ignored and rejected if tracked | Not run |
| CI | Workflow has Python, integration, infrastructure and image gates | Hosted status for this SHA is unknown; required Stream-specific jobs are incomplete | Generated-artifact assertion is blocking in Python quality | Local checks only |
| Repository hygiene | `git ls-files` reported zero tracked Console `node_modules` files, although an ignored local installation existed | Generated artifacts were not comprehensively ignored or asserted in CI | Removed the local directory; expanded ignores; added deterministic tracked-file checker and policy | `python scripts/check_generated_artifacts.py` |
| Message inspection | Foundation policy is disabled by default | Development-only constrained inspection and leakage proof pending | No payload-reading capability added | Existing policy tests only |
| Security/tenant isolation | Security model, redaction utilities and tenant-aware repositories exist | Required real-stack cross-tenant, payload, JAAS, Connect-secret, XSS and SSRF evidence pending | No payload, destructive Kafka operation, or secret-bearing output added | Local security tests only |

## Gate decision

The Stream 360 integration gate remains **open**. This change corrects concrete storage and repository-hygiene blockers,
but does not treat those corrections as evidence for the missing APIs, Console, SSE, collectors, or real-stack tests.
DataObs is not claimed to be production-ready, no additional messaging provider is claimed, and autonomous or
destructive remediation remains out of scope.
