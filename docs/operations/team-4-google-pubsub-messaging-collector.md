# Operate the Google Pub/Sub collector

Install `requirements-gcp-pubsub.txt`, configure explicit project IDs using the example configuration, and select ADC,
Workload Identity Federation, or service-account impersonation. Legacy keys require the explicit compatibility flag
and an environment secret reference. Never place credential JSON inline.

Collection is bounded by projects, topics, subscriptions, pages, observations, monitoring series/points, request time,
and total time. Partial project, Monitoring, metric, or visibility failures produce safe partial evidence and preserve
successful sibling inventory. Collection Manager persists observations and run evidence before advancing its existing
OCC checkpoint; suggested scopes begin `gcp/project/<project>/pubsub/`.

Live validation is opt-in with `RUN_GCP_PUBSUB_INTEGRATION_TESTS=1` and externally provisioned allowlisted resources.
Absence of credentials means not run, not pass. Emulator results do not certify IAM or Cloud Monitoring.
