# Operating the AWS data platform collector

Use the disabled synthetic example in `config/integrations/aws-data-platform.example.yaml`. Supply tenant and environment
only through trusted runtime variables, and use the normal AWS credential chain (instance role or web identity). An
optional AssumeRole external ID is resolved from an environment reference; it is never configuration evidence.

The Collection Manager CLI offers `validate-config`, `test-connection`, `collect-once`, `worker`, and `status`. It fails
closed without Elasticsearch, terminal migration 0022, durable repositories, tenant, and environment. SIGTERM/SIGINT
stop work at collection boundaries. Scheduler composition must cap concurrency and prevent overlapping execution of
the same tenant/environment/integration/account/region/service scope.

Troubleshoot stable codes rather than raw AWS messages: verify STS identity/account, explicit regions, service IAM,
endpoint reachability and throttling quotas. Access denial for one service and CloudWatch failure are partial; failed
scope checkpoints do not advance. Roll back by stopping AWS writers/workers and retaining evidence/checkpoints for
audit; do not remove migration 0022 during normal rollback.

For v2/v3, inspect S3 prefix `sample_truncated` before interpreting freshness; raise limits only within validated caps.
Missing S3 request metrics normally means request metrics are not configured, not zero traffic. SageMaker and Redshift
history lookbacks overlap to capture terminal updates and deduplicate on stable AWS IDs. MWAA collection never contacts
Airflow. If optional history is denied, retain inventory and fix only that IAM scope. Metric windows tolerate delayed
daily S3 points and distinguish measured zero, missing, stale, unsupported, and partial evidence.

Known limitations include no live-AWS certification, organisation crawling, arbitrary metrics/APIs, logs, SQL/data
access, profiling, lineage, cost, mutation, UI onboarding, or release packaging. Team 0 must add Docker/Helm packaging;
Team 2 may consume MWAA environment identity for later Airflow normalisation; Team 5 may later add onboarding.

V3 messaging operation details and payload-blind IAM are documented in the Team 4 Kinesis/SQS operations and security guides.
