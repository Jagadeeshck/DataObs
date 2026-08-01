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

Known limitations include no live-AWS certification, organisation crawling, arbitrary metrics/APIs, logs, SQL/data
access, profiling, lineage, cost, mutation, UI onboarding, or release packaging. Team 0 must add Docker/Helm packaging;
Team 2 may consume source evidence for Glue/Spark normalisation; Team 5 may later add onboarding.
