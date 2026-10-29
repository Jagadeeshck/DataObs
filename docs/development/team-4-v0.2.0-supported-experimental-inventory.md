# Team 4 v0.2.0 supported versus experimental inventory

## Release-profile candidates

These are the only collection paths Team 4 recommends keeping in the v0.2.0 release discussion:

| Path | Team 4 position | Final owner gate |
|---|---|---|
| Integration SDK | foundation candidate | Team 4 exact-head certification, then Team 0 release review |
| OpenTelemetry ingestion | OWNER_HANDOFF | Team 0 packaging/image/config certification |
| OpenLineage ingestion | OWNER_HANDOFF | Team 2 contract evidence and Team 0 release certification |
| Kafka observation | OWNER_HANDOFF | Team 1 must close its current failing backend/security certification and Team 0 must certify package |
| PostgreSQL scanning | BLOCKED | Team 4 packaged runtime durability plus live proof; otherwise excluded |

No entry in this table is a public `SUPPORTED` claim.

## PostgreSQL exclusion rule

PostgreSQL stays out of the v0.2.0 supported connector profile unless all of the following become true on the exact release SHA:

1. the packaged Scanner Worker actually executes scheduled scans;
2. lease/fencing state is durable and distributed-worker safe;
3. checkpoint/restart recovery is demonstrated;
4. duplicate task execution is safe;
5. the repaired mandatory workflow passes;
6. a live disposable PostgreSQL run passes;
7. the resulting evidence is retained and independently reviewable.

The current audited runtime does not meet items 1-3, so the default release decision is **exclude PostgreSQL rather than delay v0.2.0 by building a new collection control plane**.

## Experimental implemented providers

The following are implemented but excluded from v0.2.0 support because their operational runtime is Collection Manager, which is not in the supported Helm package:

- AWS data platform, Kinesis and SQS
- Google Pub/Sub
- RabbitMQ
- Azure data platform
- Snowflake
- Databricks
- BigQuery
- Trino
- Presto
- MySQL
- MariaDB
- Microsoft SQL Server
- Oracle

Their existing workflows remain valuable implementation regression gates. They are not release certification by themselves.

## Hosted-pass interpretation

At audited main `919b1e5f1f069ceb76830b92f8eb44e423e15a90`:

- Integration SDK certification passed.
- Google Pub/Sub passed, but its evidence explicitly says live integration was not run.
- Azure passed, but its evidence explicitly says live Azure was not run.
- RabbitMQ passed unit/contract checks but its workflow does not retain a live-provider certification artifact.

Those facts support `functional_unvalidated`, not supported-provider status.

## Blocked and owner-handoff items

### Team 4

- PostgreSQL certification caller omitted canonical runtime dependencies; fixed on `codex/release-team4-integrations`.
- PostgreSQL packaged Scanner Worker lacks a proven durable scheduling/lease path.
- Final-head Integration SDK and PostgreSQL workflow results are required after this PR is opened.

### Team 0

- Collection Manager is not packaged; no v0.2.0 cloud/warehouse/modern-database provider can be promoted through it.
- Bundled OTel Collector image/version/digest must be validated and pinned.
- Final supported-platform and release GO/NO_GO remain Team 0-owned.

### Team 1

- Kafka Observer backend certification run 40671870669 failed.
- The reviewed failure includes cross-tenant legacy rule access/deletion assertions.
- Team 4 does not change Team 1/security contracts.

### Team 2

- OpenLineage ingestion semantics and job/run projections are Team 2-owned.
- Team 4 consumes their release evidence; it does not redefine the OpenLineage contract.

## Recommended v0.2.0 posture

Keep the release connector story deliberately small:

- OpenTelemetry ingestion, subject to Team 0 package certification.
- OpenLineage ingestion, subject to Team 2/Team 0 exact-SHA evidence.
- Kafka observation, subject to Team 1 closing its current certification failure.
- PostgreSQL only if its packaged runtime blocker is closed without broadening the release.

Everything else remains experimental for v0.2.0.


## Final Team 4 closure decision

Closure baseline: `f62acd9f0d32ec827c26b7c8ccc56b18ac0c9401`.

### Team 4 supported connectors for v0.2.0

**None.**

The Integration SDK is a release foundation and is being separately exact-SHA certified, but it is not itself a connector. Team 4 does not recommend promoting any provider connector until its actual runtime is both packaged and live-certified.

### Explicit v0.2.0 exclusions

The following remain implemented/experimental and are explicitly excluded from Team 4 support claims:

- AWS data platform, Kinesis and SQS;
- Snowflake;
- Databricks;
- BigQuery;
- Google Pub/Sub;
- Azure data platform;
- Trino;
- Presto;
- MySQL;
- MariaDB;
- Microsoft SQL Server;
- Oracle;
- RabbitMQ.

Reason: their operational runtime is Collection Manager, and Collection Manager remains excluded from the supported Helm package.

PostgreSQL is also excluded. Its Python 3.11/3.12 contract suite passed in run `40841108301`, but the live service job was skipped and the packaged Scanner Worker does not yet demonstrate a durable distributed scheduler plus persistent lease/fencing/restart recovery.

### Owner-gated collection paths

These may be part of the product's first release only if their owning teams close their release gates:

- **OpenTelemetry** — Team 0 package/image/configuration evidence.
- **OpenLineage** — Team 2 canonical job/run contract evidence plus Team 0 package/release evidence. Team 2 job-run backend run `40862723962` passed on the closure baseline.
- **Kafka** — Team 1 runtime evidence plus Team 0 package evidence. Team 1 stream-observer run `40862723897` failed on the closure baseline and therefore remains owner-gated.

### Optional failures

Optional provider workflow failures are classified, retained and reported; they are not silently ignored. They do not become v0.2.0 release blockers unless the provider is declared part of the supported profile or the failure exposes a shared SDK/runtime defect.

The Azure capability-declaration failure was a shared SDK contract defect and is fixed in this closure branch. Provider-specific environment failures for excluded experimental providers remain visible but do not expand the v0.2.0 connector scope.


## Sprint 3 final support boundary

Baseline: `855345eb02250f9a738abe44bd520247243032bf`.

### Packaged and certified

No Team 4 provider connector currently qualifies.

The Integration SDK is mandatory release infrastructure and has a current-main hosted pass, but it is not itself a connector.

### Implemented but unvalidated

These providers have healthy hosted contract/fixture evidence but remain outside supported v0.2.0 because their runtime is not in the supported package and/or live service proof is absent:

- Google Pub/Sub — hosted pass `40961601012`; live external fixture not established.
- Azure data platform — hosted pass `40961601165`; live synthetic Azure proof not established.
- RabbitMQ — hosted pass `40961601051`; no retained live RabbitMQ provider certification.
- PostgreSQL — contract workflow `40841108301` passed on Python 3.11/3.12, but live job was skipped and packaged scheduler/lease durability remains unproven.

### Experimental

AWS, Snowflake, Databricks, BigQuery, Trino, Presto, MySQL, MariaDB, SQL Server and Oracle remain implemented/experimental. They are not part of the v0.2.0 supported package and do not have the complete packaged-runtime plus live exact-release-SHA proof required for promotion.

### Explicitly excluded from v0.2.0 Team 4 support claims

All Team 4 provider connectors are excluded from the supported v0.2.0 connector set.

Collection Manager remains explicitly excluded from the Team 0 Beta deployment package. Consequently no provider whose only operational path is Collection Manager can be promoted by Team 4 in this release.

PostgreSQL is separately excluded because its packaged Scanner Worker does not yet demonstrate durable distributed scheduling, persistent lease/fencing and restart-safe recovery.

### Owner-gated product collection paths

OpenTelemetry, OpenLineage and Kafka are not Team 4 provider promotions.

- OpenTelemetry support wording follows Team 0 package/image certification.
- OpenLineage follows Team 2 job/run/lineage certification plus Team 0 release authority.
- Kafka follows Team 1 stream-observer certification plus Team 0 release authority.

Team 0 remains the only authority that can publish a supported platform or change the overall NO_GO/GO decision.
