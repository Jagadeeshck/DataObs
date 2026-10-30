# Team 4 v0.2.0 integration release audit

## Scope

Team 4 audited the integration and collection surface for the DataObs v0.2.0 first supported release. This audit is release-scope work, not provider expansion.

- Audited `main`: `919b1e5f1f069ceb76830b92f8eb44e423e15a90`
- Working branch: `codex/release-team4-integrations`
- Application/chart: `0.2.0`
- Executable terminal migration at audit time: `0033_team1_stream_schema_intelligence_runtime`
- Repository release state at audit time: `NO_GO`; no supported platform is yet published.
- No provider or released migration is added or changed by this release-scope audit.

## Ownership and packaging

Team 4 owns the Integration SDK, Collection Manager provider integrations and Scanner Worker/PostgreSQL integration. Kafka belongs to Team 1; OpenLineage/job semantics belong to Team 2; Helm packaging, supported-platform declarations and final release promotion belong to Team 0.

The v0.2.0 Helm package includes API, Console, Quality Worker, Scanner Worker, Monitor Runtime, Pathway Worker, Kafka Observer, optional OpenTelemetry Collector and the migration Job. Collection Manager is explicitly excluded from the supported package.

That packaging boundary means a provider registered only in Collection Manager cannot be called supported in v0.2.0, regardless of unit, fixture or hosted workflow success.

## Implemented provider registry

The audited Collection Manager registry contains 14 Team 4 providers:

`aws` v3, `snowflake` v1, `databricks` v1, `bigquery` v1, `gcp` v1, `azure` v1, `trino` v1, `presto` v1, `postgres` v1, `mysql` v1, `mariadb` v1, `sqlserver` v1, `oracle` v1 and `rabbitmq` v1.

Every audited provider declares a non-empty supported capability set, a disjoint unsupported set, at least one collection mode, and together the supported/unsupported sets cover the complete Integration SDK capability enum. A release regression test now enforces this invariant for the registered provider set.

## Integration SDK findings

The SDK already provided bounded retry, elapsed retry limits, timeout enforcement, cancellation propagation, explicit provider registration, capability negotiation, tenant/integration context validation, recursive redaction helpers, observation-count limits and OCC-capable checkpoint contracts.

This branch adds one fail-closed runtime guard: a provider that yields an object outside the supported observation contract is rejected with `malformed_provider_response` before observation persistence, run persistence or checkpoint advancement.

Regression coverage also proves that an observation-persistence failure prevents run persistence and checkpoint advancement.

## Hosted evidence reviewed

| Workflow | Run | SHA | Result | What it proves | What it does not prove |
|---|---:|---|---|---|---|
| Integration SDK certification | 40671870750 | `919b1e5f...` | pass | hosted Integration SDK fixture/contract suite and exact-SHA envelope | live provider certification |
| Google Pub/Sub collector | 40671870728 | `919b1e5f...` | pass | hosted provider/unit/contract tests | evidence explicitly records `live_integration_status=not_run`; Collection Manager is not packaged |
| RabbitMQ collector | 40671870655 | `919b1e5f...` | pass | hosted provider/unit/contract tests | workflow retains no live RabbitMQ certification artifact; Collection Manager is not packaged |
| Azure data-platform collector | 40671870703 | `919b1e5f...` | pass | hosted provider/unit/contract tests and self-verification | evidence explicitly records `live_azure_test_status=not_run`; Collection Manager is not packaged |
| PostgreSQL relational foundation | 40583054174 | PR #308 merge candidate | fail | exposed a certification workflow dependency defect | no provider/runtime certification; live job skipped |
| Team 1 stream-observer backend | 40671870669 | `919b1e5f...` | fail | current Kafka release evidence is not clean | failure is Team 1/security-owned, not a Team 4 provider defect |

## PostgreSQL failure root cause

The PostgreSQL workflow failed before test execution because it installed only `requirements-postgres.txt`. Collection Manager imports require canonical runtime dependencies, and test collection failed with:

`ModuleNotFoundError: No module named 'pydantic'`.

Both Python 3.11 and 3.12 jobs failed for the same reason. The live PostgreSQL job was skipped.

This branch fixes the Team 4 caller to install:

`requirements.txt + requirements-ci.txt + requirements-postgres.txt`

without skipping or weakening any tests.

## PostgreSQL packaged-runtime blocker

The PostgreSQL Scanner Worker is packaged, but the audited production command is not yet a durable scan scheduler:

- Helm runs `python -m services.scanner_worker.cli ... run`.
- The current `run` path emits heartbeats and sleeps; it does not acquire durable scheduled tasks and execute scans.
- `ScannerWorker` defaults to `InMemoryLeaseManager`, whose source explicitly states it is development/test-only and unsafe for distributed workers.
- No durable packaged lease/fencing path was found for this Scanner Worker execution mode.

Therefore PostgreSQL remains **BLOCKED** for v0.2.0 supported status even if its repaired fixture/integration workflow becomes green. A live database test cannot compensate for an unproven packaged scheduling/restart path.

## OpenTelemetry handoff

The optional OTel Collector is represented in the Helm package, but release support remains Team 0-owned. The audited values use `otel/opentelemetry-collector-contrib` with a DataObs-style `0.2.0` tag and placeholder release digest in production values. Team 0 must validate and pin a real compatible upstream Collector image/configuration before bundled OTel can be promoted.

Team 4 therefore records OTel as `OWNER_HANDOFF`, not supported.

## OpenLineage handoff

`POST /api/v1/openlineage/events` is packaged through the API and is the canonical OpenLineage ingestion endpoint. Authentication, tenant/environment injection, bounded/redacted event handling and canonical job/run semantics are Team 2/API contracts. Team 4 does not redefine them.

OpenLineage is `OWNER_HANDOFF` pending Team 2 and Team 0 final exact-SHA release evidence.

## Kafka handoff

Kafka Observer is packaged and Team 1-owned. The latest reviewed Team 1 stream-observer run, 40671870669, failed. The observed failure was in a security/tenant-isolation suite: legacy rules could expose or delete another tenant's rule when no tenant selector was supplied.

Team 4 does not alter Team 1 or shared security contracts. Kafka is `OWNER_HANDOFF` until Team 1/security evidence is clean on the release SHA.

## v0.2.0 Team 4 conclusion

- Integration SDK: release foundation candidate; final branch evidence still required.
- OpenTelemetry: owner handoff to Team 0.
- OpenLineage: owner handoff to Team 2/Team 0.
- Kafka: owner handoff to Team 1/Team 0.
- PostgreSQL: blocked; exclude from supported connector profile until packaged runtime durability is proven.
- Collection-Manager-only providers: implemented/experimental and excluded from v0.2.0 supported connector claims.

A green fixture workflow is never used as a live-provider support claim.


## SDK/provider closure pass — 2026-10-29

This closure pass rebased the Team 4 release review on current `main`:

- audited SHA: `f62acd9f0d32ec827c26b7c8ccc56b18ac0c9401`;
- latest Integration SDK certification: run `40862724272`, **failed**;
- first meaningful failure: `test_registered_provider_capability_declarations_are_complete`;
- result: 107 passed, 10 skipped, 1 failed;
- root cause: Azure v1 omitted `SCHEMA_DISCOVERY` from both its supported and unsupported capability sets;
- closure fix: classify `SCHEMA_DISCOVERY` as unsupported and lock the declaration with a provider-specific regression.

The failure is a capability declaration defect, not evidence that Azure implements schema discovery. The release contract requires every provider to classify every SDK capability explicitly so unsupported operations fail closed.

### SDK runtime re-verification

The current SDK/runtime regression suite verifies:

- explicit provider registration and unsupported capability rejection;
- trusted tenant/integration identity cannot be overridden by provider configuration;
- recursive, bounded secret redaction;
- deterministic identities and bounded pagination;
- measured zero remains distinct from missing evidence;
- bounded retry with non-retryable authentication failures;
- retry cancellation propagation;
- runtime collection timeout and cancellation propagation;
- duplicate suppression;
- malformed provider observations fail with `malformed_provider_response` before persistence;
- failed observation persistence prevents run persistence and checkpoint advancement;
- OCC checkpoint semantics remain tenant/integration scoped.

No retry, timeout, cancellation, redaction, tenant-boundary or persistence-ordering behavior was weakened in this closure pass.

### PostgreSQL closure evidence

PR #314 PostgreSQL workflow run `40841108301` passed both Python 3.11 and Python 3.12 contract jobs after the workflow dependency/tooling repair. The live PostgreSQL job remained skipped.

This does **not** change PostgreSQL's release status. The packaged Scanner Worker still executes `services.scanner_worker.cli ... run`, whose current runtime is heartbeat-oriented rather than a durable distributed scheduling loop. `ScannerWorker` still defaults to `InMemoryLeaseManager`, explicitly development/test-only. No durable distributed lease/fencing and restart-safe scheduler path is packaged.

PostgreSQL therefore remains **BLOCKED / experimental for v0.2.0 support**.

### Current owner coordination

At `f62acd9f...`:

- Team 2 `job-run-backend` run `40862723962` passed; OpenLineage remains Team 2/Team 0 release-owned.
- Team 1 `stream-observer-backend` run `40862723897` failed; Kafka remains an owner handoff rather than a Team 4 support claim.
- Team 0 deployment packaging run `40862723886` failed; final package/support promotion remains Team 0-owned.
- Collection Manager remains excluded from `docs/release/beta-deployment-package.md`.

### Exact Team 4 boundary

For v0.2.0, Team 4 recommends:

1. Integration SDK — release foundation only, pending exact-head hosted PASS from this closure branch.
2. PostgreSQL — excluded from supported connectors; contract-tested but packaged runtime durability is not proven.
3. AWS, Snowflake, Databricks, BigQuery, GCP/PubSub, Azure, Trino, Presto, MySQL, MariaDB, SQL Server, Oracle and RabbitMQ — implemented but experimental because their operational path is Collection Manager, which is not in the supported Helm package.
4. OpenTelemetry, OpenLineage and Kafka — possible first-release collection/ingestion paths only through their owning teams' exact-SHA packaging and runtime certification; Team 4 does not promote them.


## Sprint 3 certification protection — 2026-10-29

Audited `main`: `855345eb02250f9a738abe44bd520247243032bf`.

### Integration SDK protected pass

The current-main Integration SDK workflow `40961601111` was explicitly re-run. Attempt 2 completed successfully on the same exact SHA.

Passed steps include:

- canonical runtime + CI dependency installation;
- SDK/Collection Manager compile;
- Ruff;
- Black;
- full `tests/integrations` suite;
- certification evidence-envelope generation;
- exact-SHA evidence verification;
- evidence artifact upload.

The retained rerun artifact is `integration-sdk-v1-evidence`, created at 2026-10-29T21:57:14Z, bound to `855345eb02250f9a738abe44bd520247243032bf` with artifact digest `sha256:8b44962a5a95cb611e2757184b5e6d3f71c68b6e610c49b4468c12b1051e0650`.

The passing contract continues to cover bounded retries, non-retryable authentication failures, cancellation propagation, collection timeouts, malformed-provider-response rejection, duplicate suppression, recursive credential redaction, trusted tenant/integration boundaries, observation/run persistence ordering and OCC checkpoint advancement.

No SDK code change was required in Sprint 3.

### Provider hosted evidence at the audited baseline

Current-main hosted contract results include:

- Azure data platform: `40961601165` — pass;
- Google Pub/Sub: `40961601012` — pass;
- RabbitMQ: `40961601051` — pass.

The supplied earlier closure runs `40869888478`, `40869888236` and `40869888078` were also successful. These results protect provider contracts; they do not establish live provider support.

### Credential redaction and least-privilege review

The Integration SDK regression suite retains recursive redaction of keys matching authorization/password/passwd/secret/token/api-key/credential/external-id patterns and bounded inline token/password redaction.

Provider support wording remains constrained by each implementation's read-only contract:

- Pub/Sub: viewer/monitoring read paths; no pull, acknowledge, seek or publish.
- RabbitMQ: monitoring-only HTTP access; no AMQP consume/basic.get/publish or message bodies.
- Azure: management-plane read operations and bounded ADLS metadata listing; no storage content reads or SQL execution.
- Database/warehouse providers: secret references, fixed/bounded metadata operations and no arbitrary business-row collection unless an explicitly documented aggregate feature is enabled.

A hosted fixture/contract pass is not substituted for live IAM/TLS/provider certification.

### Packaged runtime reconciliation

Team 0's `docs/release/beta-deployment-package.md` still excludes Collection Manager. Therefore AWS, Snowflake, Databricks, BigQuery, GCP/PubSub, Azure, Trino, Presto, MySQL, MariaDB, SQL Server, Oracle and RabbitMQ remain outside the supported v0.2.0 provider set.

PostgreSQL remains separately excluded. Its contract suite is green, but the packaged Scanner Worker still lacks a demonstrated durable distributed scheduler and persistent lease/fencing/restart path.

### Team 0 wording

Team 4 adopts Team 0's current release authority verbatim in substance:

- v0.2.0 remains `NO_GO` until Gate 0 is green for one exact SHA;
- no supported platform is published until Team 0 promotes one;
- historical/provider-local passes do not override Gate 0;
- Team 4 does not independently publish a supported-platform claim.

### Sprint 3 conclusion

Team 4's supported connector recommendation for v0.2.0 remains **none**.

The Integration SDK is certified as a mandatory release foundation on the audited exact SHA. Provider implementations remain implemented/unvalidated, experimental or excluded according to packaging and live-evidence status; no optional provider failure is reclassified to bypass mandatory release policy.


## Sprint 4 provider-scope revalidation — 2026-10-30

Audited `main`: `c3d3dfe63b2d8227612dc867988db268c8b7424f`.

### Exact-SHA Integration SDK evidence

Integration SDK workflow `41120485748` was explicitly re-run on the audited SHA. Attempt 2 completed successfully.

- workflow conclusion: `success`;
- exact producer SHA: `c3d3dfe63b2d8227612dc867988db268c8b7424f`;
- job: `certify` — pass;
- retained artifact: `integration-sdk-v1-evidence`;
- artifact created: 2026-10-30T21:26:28Z;
- artifact digest: `sha256:92e353527658d0f6416d7ff6ce7b27d8ddb1caffee4824b63b25d5d0dfb47298`.

The certified suite preserves the established SDK invariants:

- complete provider capability declarations across the registered provider set;
- explicit unsupported-capability rejection, including Azure `SCHEMA_DISCOVERY`;
- bounded retries and non-retryable authentication failures;
- cancellation propagation;
- collection timeout enforcement;
- malformed-provider-response rejection before persistence;
- duplicate suppression;
- recursive credential redaction;
- trusted tenant/integration boundaries;
- observation and run persistence before checkpoint advancement;
- OCC checkpoint semantics.

No SDK validation was weakened and no provider capability was expanded in Sprint 4.

### Exact packaged runtime

The Team 0 Beta deployment package still contains:

- API;
- Console;
- Quality Worker;
- Scanner Worker;
- Monitor Runtime;
- Pathway Worker;
- Kafka Observer;
- optional OpenTelemetry Collector;
- migration Job.

Elasticsearch remains external. Collection Manager, embedded Elasticsearch, Kibana, identity provider, ingress controller, Grafana Alloy, demos and POCs remain excluded.

Therefore a passing Collection Manager provider workflow remains implementation/contract evidence, not proof that the provider is supported by the v0.2.0 package.

### Current provider contract evidence

On the audited exact main SHA, current hosted contract results include:

- Azure data platform `41130816932` — pass;
- Google Pub/Sub `41130816933` — pass;
- RabbitMQ `41130816949` — pass.

These workflows do not establish live provider certification.

### PostgreSQL runtime re-assessment

The packaged Scanner Worker remains unsuitable for a v0.2.0 PostgreSQL support claim:

- Helm invokes `python -m services.scanner_worker.cli --config ... run`;
- the `run` command emits periodic heartbeat JSON and does not acquire or execute durable scheduled tasks;
- one-shot execution exists separately through `scan-once`;
- `ScannerWorker` defaults to `InMemoryLeaseManager`;
- that implementation is explicitly documented as development/test-only and unsafe for distributed workers;
- repository search found no durable Scanner Worker lease/fencing backend.

The existing PostgreSQL contract result remains useful implementation evidence, but no live service result plus no production scheduler/lease path means PostgreSQL stays excluded.

### Optional-provider policy

The existing certification manifest marks the Team 4 Integration SDK mandatory and AWS collection optional because live AWS certification and packaged Collection Manager are absent. Sprint 4 preserves that policy: optional provider failures are visible and classified, but they do not become supported by omission and do not bypass mandatory release gates.

### Cross-team release state

At the audited baseline:

- Team 1 stream-observer run `41120485524` passed;
- Team 2 job-run backend run `41120485697` passed;
- Team 0 deployment-packaging run `41120485485` failed;
- generated production-readiness still reports `NO_GO`, candidate not frozen, supported platforms none.

Team 4 therefore does not alter supported-platform wording or Helm packaging. Any Collection Manager packaging change remains a Team 0 approval item.

### Sprint 4 conclusion

No corrective provider or SDK code change is required.

Team 4's v0.2.0 provider support boundary remains:

- Integration SDK: exact-SHA certified release foundation;
- Team 4 provider connectors: no packaged-and-certified provider;
- Collection Manager-only providers: excluded from supported status;
- PostgreSQL: excluded because packaged runtime durability is unproven;
- fixture/contract passes: retained as implementation evidence only.
