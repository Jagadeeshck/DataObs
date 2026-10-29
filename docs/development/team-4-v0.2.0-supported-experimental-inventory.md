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
