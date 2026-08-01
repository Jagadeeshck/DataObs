# Team 0 platform operations v1 preflight audit

Audited base: `043a4e368d40f0fe04d8d48610b1af613985357b`. This is a source audit, not hosted certification.

## Existing and reusable

* `src/telemetry.py` already bootstrapped OpenTelemetry traces, metrics and logs over bounded OTLP/gRPC batches; it is the canonical backend bootstrap and is hardened rather than duplicated. Capability telemetry modules remain emitters, not SDK owners.
* FastAPI preserves a validated or generated `X-Request-ID`; explicit route policy fails closed. `/livez`, `/readyz`, and deprecated `/health` existed. Security audit events and tenant context are reusable.
* Helm packages API, Console, quality worker, scanner worker, monitor runtime, pathway worker, Kafka observer, optional collector and migration Job. It already has default-deny-style NetworkPolicy, secret references, and API probes.
* Collection, monitor, pathway and Kafka runtimes have component-specific loops, leases/checkpoints and retry behavior. Backup/restore scripts, migration registry/checksums, release manifest/decision machinery and exact-SHA evidence envelopes already exist.
* PR #212 browser telemetry is under `ui/dataobs-console`; Team 0 does not modify or duplicate it.
* The capability ledger, certification manifest/workflows and the supported-platform matrix provide reusable truth/evidence boundaries. The matrix has no certified combinations.

## Incomplete at the base

The bootstrap defaulted to an implicit local collector, was not idempotent, and lacked canonical attribute enforcement and exporter status. Readiness exposed raw dependency exceptions, did not cache remote checks, and had no startup contract. Workers had inconsistent telemetry vocabulary and no common heartbeat projection. Helm telemetry schema was shallow and monitoring CRDs were absent.

## Missing at the base

Machine-readable platform metric/SLO/alert catalogues, deterministic error-budget rules, explicit platform-operations permission/API, safe support bundle, operations runbooks, and an exact-SHA Team 0 operations workflow were absent.

## Ownership and dependencies

Team 0 owns the runtime, health schema, policy, catalogues, Helm resources, release/backup summaries, support utility and certification harness. The platform operations API and permission are shared contracts. Teams 1–4 must adopt the common worker wrapper without changing business semantics; measured zero must remain distinct from missing evidence. Team 5 may consume the documented API but retains Console/browser ownership. No Team 5 source is changed.

## Migration and hosted evidence decision

No Elasticsearch resource is needed for metric-only heartbeats, so no released migration is edited and no forward migration is added. Durable worker status remains a future dependency where existing authoritative checkpoints cannot answer it. Hosted secured-Elasticsearch, OIDC, recovery, upgrade, OTLP failure injection, Kind and SLO evidence is unavailable for this head and remains **pending/unvalidated**. Nothing here changes `supported:` or establishes production readiness.
