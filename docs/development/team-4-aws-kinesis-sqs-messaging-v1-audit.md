# Team 4 AWS Kinesis and SQS messaging v1 audit

- **Team / task:** Team 4 — Integrations and Collection; `Team 4: Build AWS Kinesis and SQS Messaging Collectors v1`.
- **Audited base SHA:** `39b7757a8cce5634bf84f17da53d745f59eefc6b`.
- **Terminal migration:** dynamically derived as `0032_team2_data_slo_production_runtime` with `python scripts/release/current_terminal_migration.py`.
- **Migration doctor:** local execution could not connect to Elasticsearch at `localhost:9200`; CI supplies Elasticsearch 9.4.2 and runs doctor. Migration immutability passed for all 31 released migrations.
- **Provider before change:** `provider_type=aws`, version `2`; registry was RDS, Glue, Athena, EMR Serverless, S3, Lambda, SageMaker, MWAA, Redshift, and Redshift Serverless. Version policy does not prohibit a contract bump, so v3 adds Kinesis and SQS.
- **CloudWatch:** the existing `CloudWatchAdapter` and closed `METRIC_REGISTRY` use `GetMetricData`, bounded queries/lookback/period, retain measured zero, and emit missing values as `None`. Messaging composes the existing service and CloudWatch clients without changing other collectors.
- **Existing Kinesis/SQS code:** Team 1 already supplied canonical contracts and provider adapters, but Team 4 had no provider collectors. The Kinesis adapter accepts stream/shard resources; the SQS adapter accepts queue/dead-letter-queue resources and forces approximate backlog semantics.
- **Team 1 envelope:** tenant/environment, messaging system, AWS provider/account/region, resource kind/provider ID/name, observed time, status/confidence/coverage, collection method/integration, and schema version. Team 4 places this allowlisted handoff in provider-native resource evidence and contract-tests it with `require_observation_envelope` and both adapters.
- **Runtime limitation:** `MultiBrokerRuntime.run` currently normalizes and persists only resource envelopes (`metric_family=resource`). It does not consume provider metric, backlog, lag, retention, or DLQ relationship families. Team 1 must add those projections; Team 4 does not duplicate normalization.
- **SDK dependency:** `boto3>=1.34,<2.0`; hosted evidence records exact boto3/botocore versions.
- **IAM:** Kinesis ListStreams/DescribeStreamSummary/ListShards/ListTagsForStream; SQS ListQueues/GetQueueAttributes/ListQueueTags; CloudWatch GetMetricData and STS GetCallerIdentity, plus optional existing AssumeRole. Payload-read and mutation permissions are expressly absent.
- **Pagination bounds:** Kinesis 500 streams/50 pages and 1,000 shards/stream/100 pages by default; SQS 1,000 queues/100 pages. All are validated, selections are explicit when supplied, and truncation is emitted.
- **CloudWatch bounds:** 900-second lookback, 300-second period, at most 100 allowlisted queries and 1,000 datapoints. Shard metrics are never enabled; shard dimensions remain opt-in only when already enabled.
- **Migration decision:** no migration. Generic Team 4 evidence/checkpoints and Team 1 storage already exist; released migrations remain untouched.
- **Known limitations:** no hosted/live AWS result; no message/record reads; no consumer identity; no offset semantics; SQS counts are approximate; iterator age is time lag rather than offset lag; visible-scope DLQs only; runtime currently projects resources only; local migration doctor needs Elasticsearch.
