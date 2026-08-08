# Elastic Workflows integration v1

DataObs targets Kibana 9.4.2 GA Workflow endpoints under `/api/workflows/workflow`. Repository-managed YAML is checksummed and statically limited to the dedicated `cases.getCase`, `cases.addComment`, and `cases.addTags` step types. Deprecated `kibana.*`, generic HTTP, scripts, shell execution, connector push and unknown steps fail validation.

Only a server-owned binding may select a workflow. User-initiated runs follow preview, policy, approval, idempotent fenced execution, provider synchronization and DataObs verification. A provider `completed` status means only that orchestration completed; desired-effect verification remains separate. Unknown provider statuses normalize to `provider_status_unknown`.
