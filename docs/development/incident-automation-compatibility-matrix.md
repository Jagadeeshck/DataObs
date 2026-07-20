# Incident automation compatibility matrix

Audit date: 2026-07-20. Target images are pinned to `docker.elastic.co/elasticsearch/elasticsearch:9.4.2` and `docker.elastic.co/kibana/kibana:9.4.2`; no floating tags are permitted. Documentation network access was unavailable in this build environment, so all provider rows remain **not tested** pending verification against current official Elastic public API documentation and a licensed real stack. DataObs must not infer availability from configuration alone.

| Capability | Product/version | Public API or feature | Required privilege | License/capability probe | Tested state |
|---|---|---|---|---|---|
| Search and durable projections | Elasticsearch 9.4.2 | Index, data stream, PIT/search-after, transform APIs | least-privilege index plus transform privileges | root info, license and privilege probes | not tested |
| Spaces | Kibana 9.4.2 | public Spaces APIs | space read | public spaces list scoped to allowlist | not tested |
| Cases | Kibana 9.4.2 | public Cases create/update/comment/push APIs | Cases read/write in selected space | API response plus Cases privilege | not tested |
| Workflows | Kibana 9.4.2 | public workflow definition/execution APIs, if exposed | workflow read/execute/manage separated | API, license, space and privilege probes | not tested |
| Connector discovery | Kibana 9.4.2 | public action connector APIs | Actions read | intersect returned IDs/types with configured allowlist | not tested |
| Workflow definitions | Kibana 9.4.2 | public import/update/export APIs, if exposed | workflow manage | endpoint and privilege probe | not tested |
| Workflow executions | Kibana 9.4.2 | public start/status/cancel APIs, if exposed | workflow execute | endpoint and privilege probe | not tested |
| Case workflow steps | Kibana 9.4.2 | `cases.*` steps | Cases plus workflow privileges | validate provider-supported step catalogue | not tested |
| Deprecated Case aliases | Kibana 9.4.2 | `kibana.*` aliases | n/a | local validator rejects them | unit tested |
| Generic Kibana request | Kibana 9.4.2 | `kibana.request` | n/a | deny by default | unit tested |
| Alert/rule trigger | Kibana 9.4.2 | public rule Workflow action, if licensed | rule read/write and workflow execute | rule type/action capability probe | not tested |
| External connectors | Kibana 9.4.2 | Jira, ServiceNow, PagerDuty, Slack, Teams, email, webhook | Actions read/execute | configured ID/type allowlist; never return secrets | not configured |
| API key auth | Elasticsearch/Kibana 9.4.2 | documented API key authentication | explicitly assigned least privilege | authenticated privilege probe | not tested |
| Service account auth | Elasticsearch 9.4.2 | documented service account token | service-specific role descriptor | authenticated privilege probe | not tested |

Capability mapping is strict: missing configuration is `not_configured`; a license denial is `unlicensed`; a connection/provider failure is `unavailable`; an absent supported API is `unsupported`; incomplete connector/step support is `partial`; only a successful end-to-end probe is `available`. Workflow execution is never simulated or reported successful.
