# Kafka Observer runtime and real-stack audit

Baseline: `26be48b` (merge of PR #98). Migrations 0001 through 0010 were inspected and remain unchanged; migration 0010 already declares the observer checkpoint, lease, collection/capability state aliases and Kafka snapshot/error data streams, so no artificial 0011 was added.

| Capability | Current implementation | Blocking gap | Implementation in this PR | Test evidence |
|---|---|---|---|---|
| Commands | Five commands | source commands absent | all required command names, bounded JSON and status | unit/compile CLI checks |
| Scheduling | bounded retry/jitter | exceptions swallowed; no renewal | renewal thread, lease-loss failure and structured error callback | scheduler unit tests |
| Inventory | real Admin metadata | separate projections | bounded inventory/group projections | admin tests |
| Offsets | analytics only | no real watermarks | assigned combinations, low/high/commit offsets, honest LSO partial state | adapter tests; real-stack gate |
| Connect | client boundary | no executable collector/action policy | bounded normalized collector and approval/allowlist/idempotent restart | collector tests |
| Registry | client boundary | no executable collector | bounded subject/version collector and semantic summaries without schema bodies | collector tests |
| Broker metrics | helper models | absent-source semantics | explicit `not_configured` result | unit test |
| Security | redaction helpers | runtime validation gaps | TLS verification, allowlists, secret references and bounded enumeration | security tests |
| Real stack | two-broker demo | no three-broker gate | dedicated three-broker KRaft/Connect/Registry/ES 9.4.2 compose fixture | Docker commands recorded in PR |
| Monitoring/RCA | shared runtimes | end-to-end evidence not established here | unchanged; remains a draft-PR blocker | not claimed |

A client, protocol or unit test is not represented here as a successful real collector probe. The draft must remain draft until all external gates have run successfully.
