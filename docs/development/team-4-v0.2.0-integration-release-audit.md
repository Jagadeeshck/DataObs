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
