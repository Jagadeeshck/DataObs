# Team 5 multi-broker console v1 audit

Audited base: `141ec426bef2f168996df122655b9bf2cb395ff7` (2026-08-13). The branch has no configured Git remote, so the local merged `main` equivalent was audited. PRs represented after visualization PR #253 are #256 (stream-to-product impact), #252 (dbt intelligence), #255 (MariaDB), and #254 (release candidate). Open PR metadata could not be queried without a remote.

## Contracts inspected

The audit covered `src/api/stream_routes.py`, `packages/streaming/contracts.py`, all adapters under `packages/streaming/adapters`, `services/stream_observer/multi_broker_runtime.py`, Stream/Intelligence/Reliability/Pathway routes, legacy Cluster/Stream/Consumer Group/Connector/Schema pages, dashboards, investigation, activity, search, watchlist, and `src/visualization`. `GET /api/v1/streams/providers` is the only bounded provider-neutral Console contract used in v1. Existing inventory/detail APIs remain Kafka shaped.

| Provider/System   | Resource concepts                                   | Runtime evidence | Reliability      | Intelligence     | Pathways            | UI v1                               |
| ----------------- | --------------------------------------------------- | ---------------- | ---------------- | ---------------- | ------------------- | ----------------------------------- |
| Kafka             | topic, partition, consumer group, broker, connector | negotiated       | API-gated        | API-gated        | authoritative links | overview + legacy inventory/details |
| Kinesis           | stream, shard, consumer                             | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |
| SQS               | queue, DLQ                                          | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |
| RabbitMQ          | exchange, queue, consumer                           | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |
| Google Pub/Sub    | topic, subscription                                 | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |
| Azure Event Hubs  | namespace, event hub, partition, consumer group     | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |
| Azure Service Bus | namespace, queue, topic, subscription, DLQ          | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |
| Pulsar            | tenant/namespace, topic, partition, subscription    | negotiated       | capability-gated | capability-gated | capability-gated    | provider overview/matrix            |

| API                             |        Provider neutral |         Kafka specific |                   Bounded | UI use                                |
| ------------------------------- | ----------------------: | ---------------------: | ------------------------: | ------------------------------------- |
| `GET /api/v1/streams/providers` |                     yes |                     no |  eight registered systems | overview, filter, capability matrix   |
| `GET /api/v1/streams`           |        partial identity |     yes metrics/facets | limit/cursor (50 default) | legacy Kafka inventory                |
| `GET /api/v1/streams/{id}/*`    |                 partial |            largely yes |       detail/subresources | legacy Topic 360                      |
| Stream Intelligence/Reliability |        capability-owned | current Kafka evidence |                   bounded | existing pages; no client calculation |
| Pathways                        | canonical relationships |                     no |                   bounded | existing authoritative handoff        |

## Baseline

All repository preflight checks passed. Terminal migration was dynamically reported as `0030_team1_multi_broker_messaging_runtime`. Console baseline validation identified the unrelated composite-build defects recorded below. Team 5 can safely change only presentation/client code and documentation; Team 1 semantics and calculations were not changed.

## Truthfulness boundaries

The UI does not manufacture non-Kafka inventories, resource identity, capability support, transitions, graph edges, reliability, forecasts, or counts. Unsupported is “Not applicable,” supported missing is “No observation,” unavailable is “Unavailable,” and measured zero remains `0`.

## Exact baseline failures

`pnpm build` reaches `tsc -b` but is blocked by existing work outside Team 5 scope:

- `src/features/quality/QualityAuxiliary.tsx` has `Coverage`/`EvidenceEnvelope` incompatibility, optional denominator/list access, and absent `coverage_percentage` (Team 2 Quality; blocks production build; Team 5 cannot safely redefine the contract).
- `src/features/quality/QualityConsole.tsx` imports absent `QualityOverviewView`; `QualityFindings.tsx` imports absent `qualityFindings` and then loses result typing; `QualityRoutes.test.ts` lacks Node type declarations; `components/QualityComponents.tsx` uses incompatible evidence fields/status (Team 2 Quality; blocks production build; unsafe for Team 5 to redesign).
- `src/investigation/providers.ts` accesses heterogeneous entity fields without narrowing (`state`, `status`, `health`, time fields) (Team 5 Investigation, but unrelated concurrent contract migration; blocks build; changing it in this focused messaging PR risks changing investigation semantics).
- `pnpm playwright` cannot start Vite preview because the failed build produces no `dist`; browser/Axe execution is consequently blocked, not skipped silently.

`pnpm typecheck` (`tsc --noEmit`) passes because it does not exercise the composite build graph that exposes these unrelated errors. Unit, lint, formatting, API generation/drift, and visualization checks pass. Bundle and performance checks require a successful production build and are therefore downstream-blocked.
